"""AWS CDK stack provisioning Step Functions state machine, Lambda helpers, and alarms."""

from pathlib import Path

from aws_cdk import (
    Duration,
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_events as events,
    aws_events_targets as events_targets,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
)
from constructs import Construct

from compute_stack import EquityLensComputeStack
from lakehouse_stack import EquityLensLakehouseStack

REPO_ROOT = Path(__file__).resolve().parents[2]
ASL_PATH = REPO_ROOT / "cloud" / "stepfunctions" / "document_pipeline.asl.json"


class EquityLensOrchestrationStack(Stack):
    """Provisions Step Functions pipeline coordinating ECS workers, Glue jobs, and Lambdas."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        lakehouse_stack: EquityLensLakehouseStack,
        compute_stack: EquityLensComputeStack,
        env_name: str = "dev",
        enable_schedule: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket = lakehouse_stack.datalake_bucket

        lambda_code = lambda_.Code.from_asset(
            str(REPO_ROOT),
            exclude=[
                ".git",
                "ui",
                "local_datalake",
                "Raw Data Extraction",
                "Data Ingestion",
                "docs",
                "misc",
                "output",
                "node_modules",
                ".venv*",
                "**/__pycache__",
            ],
        )

        common_env = {
            "STORAGE_BACKEND": "s3",
            "S3_BUCKET": bucket.bucket_name,
            "AWS_REGION": self.region,
        }

        list_pending_fn = lambda_.Function(
            self,
            "ListPendingDocumentsFn",
            function_name=f"equity-lens-list-pending-{env_name}",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="cloud.stepfunctions.list_pending.handler",
            code=lambda_code,
            timeout=Duration.seconds(60),
            memory_size=256,
            environment=common_env,
        )
        bucket.grant_read(list_pending_fn, "manifests/*")

        mark_quarantined_fn = lambda_.Function(
            self,
            "MarkDocumentFailedFn",
            function_name=f"equity-lens-mark-quarantined-{env_name}",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="cloud.stepfunctions.mark_quarantined.handler",
            code=lambda_code,
            timeout=Duration.seconds(60),
            memory_size=256,
            environment=common_env,
        )
        bucket.grant_read_write(mark_quarantined_fn, "manifests/*")
        bucket.grant_read_write(mark_quarantined_fn, "quarantine/*")

        sfn_role = iam.Role(
            self,
            "StepFunctionsPipelineRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )
        list_pending_fn.grant_invoke(sfn_role)
        mark_quarantined_fn.grant_invoke(sfn_role)

        pass_roles = [compute_stack.task_definition.task_role.role_arn]
        if compute_stack.task_definition.execution_role is not None:
            pass_roles.append(compute_stack.task_definition.execution_role.role_arn)

        sfn_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecs:RunTask"],
                resources=[compute_stack.task_definition.task_definition_arn],
            )
        )
        sfn_role.add_to_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=pass_roles,
            )
        )
        sfn_role.add_to_policy(
            iam.PolicyStatement(
                actions=["events:PutTargets", "events:PutRule", "events:DescribeRule"],
                resources=[f"arn:aws:events:{self.region}:{self.account}:rule/StepFunctionsGetEventsForECSTaskRule"],
            )
        )
        sfn_role.add_to_policy(
            iam.PolicyStatement(
                actions=["glue:StartJobRun", "glue:GetJobRun", "glue:GetJobRuns", "glue:BatchStopJobRun"],
                resources=[
                    f"arn:aws:glue:{self.region}:{self.account}:job/{job_name}"
                    for job_name in lakehouse_stack.glue_job_names.values()
                ],
            )
        )

        public_subnets = compute_stack.vpc.public_subnets
        subnet_1 = public_subnets[0].subnet_id
        subnet_2 = public_subnets[1].subnet_id if len(public_subnets) > 1 else subnet_1

        definition_substitutions = {
            "ListPendingLambdaArn": list_pending_fn.function_arn,
            "MarkQuarantinedLambdaArn": mark_quarantined_fn.function_arn,
            "EcsClusterArn": compute_stack.cluster.cluster_arn,
            "WorkerTaskDefinitionArn": compute_stack.task_definition.task_definition_arn,
            "SubnetId1": subnet_1,
            "SubnetId2": subnet_2,
            "SecurityGroupId": compute_stack.security_group.security_group_id,
            "WorkerContainerName": compute_stack.container_name,
            "CurateFinancialsJobName": lakehouse_stack.glue_job_names["curate_financials"],
            "CurateFactsJobName": lakehouse_stack.glue_job_names["curate_facts"],
            "CurateChunksJobName": lakehouse_stack.glue_job_names["curate_chunks"],
            "ComputeDeviationsJobName": lakehouse_stack.glue_job_names["compute_deviations"],
        }

        asl_definition = ASL_PATH.read_text(encoding="utf-8")
        cfn_sm = sfn.CfnStateMachine(
            self,
            "DocumentPipelineStateMachine",
            state_machine_name=f"equity-lens-pipeline-{env_name}",
            role_arn=sfn_role.role_arn,
            definition_string=asl_definition,
            definition_substitutions=definition_substitutions,
        )

        cloudwatch.Alarm(
            self,
            "PipelineFailureAlarm",
            alarm_name=f"equity-lens-pipeline-failures-{env_name}",
            metric=cloudwatch.Metric(
                namespace="AWS/States",
                metric_name="ExecutionsFailed",
                dimensions_map={"StateMachineArn": cfn_sm.attr_arn},
                statistic="Sum",
                period=Duration.minutes(5),
            ),
            threshold=1,
            evaluation_periods=1,
        )

        if enable_schedule:
            sm_ref = sfn.StateMachine.from_state_machine_arn(
                self, "ScheduledStateMachineRef", cfn_sm.attr_arn
            )
            events.Rule(
                self,
                "DailyPipelineSchedule",
                rule_name=f"equity-lens-daily-pipeline-{env_name}",
                schedule=events.Schedule.cron(minute="0", hour="2"),
                targets=[events_targets.SfnStateMachine(sm_ref)],
            )
