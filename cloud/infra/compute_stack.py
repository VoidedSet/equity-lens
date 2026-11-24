"""AWS CDK stack provisioning ECR, zero-NAT VPC, ECS Fargate Cluster, and Worker Task Definition."""

from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_logs as logs,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class EquityLensComputeStack(Stack):
    """Provisions containerized ECS/Fargate compute for document extraction and Supabase sync."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        datalake_bucket: s3.IBucket,
        env_name: str = "dev",
        bedrock_region: str = "ap-south-1",
        bedrock_model_id: str = "google.gemma-3-27b-it",
        supabase_secret_name: str = "",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        secret_name = supabase_secret_name or f"equity-lens/supabase-{env_name}"

        self.ecr_repo = ecr.Repository(
            self,
            "WorkerEcrRepo",
            repository_name=f"equity-lens-worker-{env_name}",
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=5)],
        )

        # Public-only VPC with 0 NAT gateways avoids monthly NAT gateway charges for outbound AWS/Supabase calls
        self.vpc = ec2.Vpc(
            self,
            "WorkerVpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                )
            ],
        )

        self.security_group = ec2.SecurityGroup(
            self,
            "WorkerSecurityGroup",
            vpc=self.vpc,
            description="Outbound-only security group for EquityLens Fargate workers",
            allow_all_outbound=True,
        )

        self.cluster = ecs.Cluster(
            self,
            "WorkerCluster",
            cluster_name=f"equity-lens-cluster-{env_name}",
            vpc=self.vpc,
        )

        log_group = logs.LogGroup(
            self,
            "WorkerLogGroup",
            log_group_name=f"/ecs/equity-lens-worker-{env_name}",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        task_role = iam.Role(
            self,
            "WorkerTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        datalake_bucket.grant_read_write(task_role, "raw/*")
        datalake_bucket.grant_read_write(task_role, "processed/*")
        datalake_bucket.grant_read_write(task_role, "curated/*")
        datalake_bucket.grant_read_write(task_role, "quarantine/*")
        datalake_bucket.grant_read_write(task_role, "manifests/*")
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                ],
            )
        )

        supabase_secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            "SupabaseSecret",
            secret_name=secret_name,
        )

        self.task_definition = ecs.FargateTaskDefinition(
            self,
            "WorkerTaskDefinition",
            family=f"equity-lens-worker-{env_name}",
            cpu=1024,
            memory_limit_mib=2048,
            task_role=task_role,
        )

        self.container_name = "worker"
        self.task_definition.add_container(
            self.container_name,
            image=ecs.ContainerImage.from_ecr_repository(self.ecr_repo, tag="latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="worker",
                log_group=log_group,
            ),
            environment={
                "STORAGE_BACKEND": "s3",
                "S3_BUCKET": datalake_bucket.bucket_name,
                "AWS_REGION": self.region,
                "BEDROCK_REGION": bedrock_region,
                "LLM_PROVIDER": "bedrock",
                "BEDROCK_MODEL_ID": bedrock_model_id,
                "SINK": "s3",
                "EMBEDDING_MODEL": "all-MiniLM-L6-v2",
            },
            secrets={
                "SUPABASE_URL": ecs.Secret.from_secrets_manager(supabase_secret, "SUPABASE_URL"),
                "SUPABASE_SERVICE_KEY": ecs.Secret.from_secrets_manager(
                    supabase_secret, "SUPABASE_SERVICE_KEY"
                ),
            },
        )
