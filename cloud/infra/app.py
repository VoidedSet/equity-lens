"""CDK application entrypoint for EquityLens AI lakehouse infrastructure."""

import os

import aws_cdk as cdk

from lakehouse_stack import EquityLensLakehouseStack

app = cdk.App()

env_name = os.getenv("CDK_ENV_NAME", "dev")
aws_region = os.getenv("AWS_REGION", "ap-south-1")
aws_account = os.getenv("CDK_DEFAULT_ACCOUNT")

EquityLensLakehouseStack(
    app,
    f"EquityLensLakehouse-{env_name}",
    env_name=env_name,
    env=cdk.Environment(account=aws_account, region=aws_region),
)

app.synth()
