"""CDK application entrypoint wiring Lakehouse, Compute (ECS/Fargate), and Step Functions stacks."""

import os

import aws_cdk as cdk

from compute_stack import EquityLensComputeStack
from lakehouse_stack import EquityLensLakehouseStack
from orchestration_stack import EquityLensOrchestrationStack

app = cdk.App()

env_name = os.getenv("CDK_ENV_NAME", "dev")
aws_region = os.getenv("AWS_REGION", "ap-south-1")
aws_account = os.getenv("CDK_DEFAULT_ACCOUNT")
bedrock_region = os.getenv("BEDROCK_REGION", aws_region)
bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", "google.gemma-3-27b-it")
enable_schedule = os.getenv("ENABLE_SCHEDULE", "false").strip().lower() in ("1", "true", "yes")

cdk_env = cdk.Environment(account=aws_account, region=aws_region)

lakehouse = EquityLensLakehouseStack(
    app,
    f"EquityLensLakehouse-{env_name}",
    env_name=env_name,
    env=cdk_env,
)

compute = EquityLensComputeStack(
    app,
    f"EquityLensCompute-{env_name}",
    datalake_bucket=lakehouse.datalake_bucket,
    env_name=env_name,
    bedrock_region=bedrock_region,
    bedrock_model_id=bedrock_model_id,
    env=cdk_env,
)

EquityLensOrchestrationStack(
    app,
    f"EquityLensOrchestration-{env_name}",
    lakehouse_stack=lakehouse,
    compute_stack=compute,
    env_name=env_name,
    enable_schedule=enable_schedule,
    env=cdk_env,
)

app.synth()
