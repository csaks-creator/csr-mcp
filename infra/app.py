import os

import aws_cdk as cdk

from stack import NovaActMcpStack

app = cdk.App()


def ctx(name: str, default: str | None = None) -> str | None:
    return app.node.try_get_context(name) or default


allowed_cidr = ctx("allowed_cidr")
if not allowed_cidr:
    raise SystemExit("Pass the CIDR allowed to reach the ALB: cdk deploy -c allowed_cidr=203.0.113.10/32")

NovaActMcpStack(
    app,
    "NovaActMcpStack",
    allowed_cidr=allowed_cidr,
    certificate_arn=ctx("certificate_arn"),
    allowed_domains=ctx("allowed_domains", ""),
    server_count=int(ctx("server_count", "2")),
    helpdesk_lambda_arn=ctx("helpdesk_lambda_arn"),
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region=os.environ.get("CDK_DEFAULT_REGION")
    ),
)

app.synth()
