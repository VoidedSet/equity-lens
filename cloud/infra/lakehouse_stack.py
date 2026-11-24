"""AWS CDK stack provisioning S3 Data Lake, Glue 5.0 ETL jobs, Glue Catalog, and Athena."""

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_athena as athena,
    aws_glue as glue,
    aws_iam as iam,
    aws_s3 as s3,
)
from constructs import Construct


class EquityLensLakehouseStack(Stack):
    """Provisions S3 Medallion lakehouse, Glue Catalog + ETL jobs, and Athena workgroup."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_name: str = "dev",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket_name = f"equity-lens-datalake-{self.account}-{env_name}".lower()

        datalake_bucket = s3.Bucket(
            self,
            "DataLakeBucket",
            bucket_name=bucket_name,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=False,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireAthenaQueryResults",
                    prefix="athena-results/",
                    expiration=Duration.days(30),
                )
            ],
        )

        glue_role = iam.Role(
            self,
            "GlueJobRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                )
            ],
        )
        datalake_bucket.grant_read_write(glue_role, "raw/*")
        datalake_bucket.grant_read_write(glue_role, "processed/*")
        datalake_bucket.grant_read_write(glue_role, "curated/*")
        datalake_bucket.grant_read_write(glue_role, "quarantine/*")
        datalake_bucket.grant_read(glue_role, "scripts/*")

        glue_db = glue.CfnDatabase(
            self,
            "EquityLensGlueDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="equity_lens",
                description="EquityLens AI curated hospitality lakehouse",
            ),
        )

        job_specs = [
            ("CurateFinancialsJob", "equity-lens-curate-financials", "curate_financials.py"),
            ("CurateFactsJob", "equity-lens-curate-facts", "curate_facts.py"),
            ("CurateChunksJob", "equity-lens-curate-chunks", "curate_chunks.py"),
            ("ComputeDeviationsJob", "equity-lens-compute-deviations", "compute_deviations.py"),
        ]

        for logical_id, job_name, script_name in job_specs:
            job = glue.CfnJob(
                self,
                logical_id,
                name=f"{job_name}-{env_name}",
                role=glue_role.role_arn,
                glue_version="5.0",
                worker_type="G.1X",
                number_of_workers=2,
                max_retries=1,
                command=glue.CfnJob.JobCommandProperty(
                    name="glueetl",
                    python_version="3",
                    script_location=f"s3://{datalake_bucket.bucket_name}/scripts/glue_jobs/{script_name}",
                ),
                default_arguments={
                    "--job-language": "python",
                    "--enable-continuous-cloudwatch-log": "true",
                    "--enable-metrics": "true",
                    "--S3_BUCKET": datalake_bucket.bucket_name,
                    "--AWS_REGION": self.region,
                    "--extra-py-files": f"s3://{datalake_bucket.bucket_name}/scripts/cloud_pkg.zip",
                    "--additional-python-modules": "pydantic>=2.7.0",
                },
            )
            job.add_dependency(glue_db)

        athena.CfnWorkGroup(
            self,
            "AthenaAnalyticsWorkGroup",
            name=f"equity-lens-analytics-{env_name}",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                enforce_work_group_configuration=True,
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{datalake_bucket.bucket_name}/athena-results/",
                ),
            ),
        )
