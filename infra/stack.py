from aws_cdk import CfnOutput, Duration, RemovalPolicy, SecretValue, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

SERVER_PORT = 8000
CLIENT_PORT = 8501
NAMESPACE = "mcp.local"


class NovaActMcpStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        allowed_cidr: str,
        certificate_arn: str | None,
        allowed_domains: str,
        server_count: int,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Tasks sit in private subnets; the NAT gateway gives the browser and Nova Act API outbound access.
        vpc = ec2.Vpc(self, "Vpc", max_azs=2, nat_gateways=1)
        cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=vpc,
            default_cloud_map_namespace=ecs.CloudMapNamespaceOptions(name=NAMESPACE),
        )

        nova_api_key = secretsmanager.Secret(
            self,
            "NovaActApiKey",
            description="Nova Act API key. Replace the placeholder after the first deploy.",
            secret_string_value=SecretValue.unsafe_plain_text("REPLACE_ME"),
        )
        mcp_token = secretsmanager.Secret(
            self,
            "McpApiToken",
            description="Bearer token shared by the MCP client and server",
            generate_secret_string=secretsmanager.SecretStringGenerator(password_length=48, exclude_punctuation=True),
        )

        # Server: Chromium needs CPU and memory headroom.
        server_task = ecs.FargateTaskDefinition(
            self,
            "ServerTask",
            cpu=2048,
            memory_limit_mib=4096,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.X86_64, operating_system_family=ecs.OperatingSystemFamily.LINUX
            ),
        )
        server_task.add_container(
            "server",
            image=ecs.ContainerImage.from_asset("../server", platform=ecr_assets.Platform.LINUX_AMD64),
            port_mappings=[ecs.PortMapping(container_port=SERVER_PORT)],
            environment={
                "ALLOWED_DOMAINS": allowed_domains,
                "MAX_CONCURRENT_SESSIONS": "2",
                "NOVA_LOGS_DIR": "/tmp/nova_act_logs",
            },
            secrets={
                "NOVA_ACT_API_KEY": ecs.Secret.from_secrets_manager(nova_api_key),
                "MCP_API_TOKEN": ecs.Secret.from_secrets_manager(mcp_token),
            },
            logging=ecs.LogDrivers.aws_logs(stream_prefix="server", log_retention=logs.RetentionDays.ONE_MONTH),
            health_check=ecs.HealthCheck(
                command=[
                    "CMD-SHELL",
                    f"python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:{SERVER_PORT}/health')\"",
                ],
                interval=Duration.seconds(30),
                start_period=Duration.seconds(30),
            ),
        )

        # The server is stateless, so tasks are interchangeable behind the ALB.
        server_service = ecs.FargateService(
            self,
            "ServerService",
            cluster=cluster,
            task_definition=server_task,
            desired_count=server_count,
            health_check_grace_period=Duration.seconds(60),
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            cloud_map_options=ecs.CloudMapOptions(name="server"),
        )

        client_task = ecs.FargateTaskDefinition(
            self,
            "ClientTask",
            cpu=512,
            memory_limit_mib=1024,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.X86_64, operating_system_family=ecs.OperatingSystemFamily.LINUX
            ),
        )
        client_task.add_container(
            "client",
            image=ecs.ContainerImage.from_asset("../client", platform=ecr_assets.Platform.LINUX_AMD64),
            port_mappings=[ecs.PortMapping(container_port=CLIENT_PORT)],
            environment={"MCP_SERVER_URL": f"http://server.{NAMESPACE}:{SERVER_PORT}/mcp"},
            secrets={"MCP_API_TOKEN": ecs.Secret.from_secrets_manager(mcp_token)},
            logging=ecs.LogDrivers.aws_logs(stream_prefix="client", log_retention=logs.RetentionDays.ONE_MONTH),
        )
        # Streamlit keeps per-browser state in memory, so keep one task (stickiness is also enabled below).
        client_service = ecs.FargateService(
            self,
            "ClientService",
            cluster=cluster,
            task_definition=client_task,
            desired_count=1,
            health_check_grace_period=Duration.seconds(60),
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
        )
        server_service.connections.allow_from(client_service, ec2.Port.tcp(SERVER_PORT), "Client to MCP server")

        # One public ALB: /mcp goes to the server, everything else to the Streamlit client.
        # The long idle timeout covers browser tasks that run for minutes.
        alb = elbv2.ApplicationLoadBalancer(
            self, "Alb", vpc=vpc, internet_facing=True, idle_timeout=Duration.seconds(600)
        )
        if certificate_arn:
            listener = alb.add_listener(
                "Https",
                port=443,
                certificates=[elbv2.ListenerCertificate.from_arn(certificate_arn)],
                open=False,
            )
            alb.add_listener(
                "HttpRedirect",
                port=80,
                open=False,
                default_action=elbv2.ListenerAction.redirect(protocol="HTTPS", port="443", permanent=True),
            )
            alb.connections.allow_from(ec2.Peer.ipv4(allowed_cidr), ec2.Port.tcp(443), "Allowed clients")
            alb.connections.allow_from(ec2.Peer.ipv4(allowed_cidr), ec2.Port.tcp(80), "HTTP redirect")
            scheme = "https"
        else:
            listener = alb.add_listener("Http", port=80, open=False)
            alb.connections.allow_from(ec2.Peer.ipv4(allowed_cidr), ec2.Port.tcp(80), "Allowed clients")
            scheme = "http"

        listener.add_targets(
            "Server",
            priority=10,
            conditions=[elbv2.ListenerCondition.path_patterns(["/mcp", "/mcp/*"])],
            port=SERVER_PORT,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[server_service],
            health_check=elbv2.HealthCheck(path="/health", healthy_http_codes="200"),
            deregistration_delay=Duration.seconds(30),
        )
        listener.add_targets(
            "Client",
            port=CLIENT_PORT,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[client_service],
            health_check=elbv2.HealthCheck(path="/_stcore/health", healthy_http_codes="200"),
            stickiness_cookie_duration=Duration.days(1),
            deregistration_delay=Duration.seconds(30),
        )

        CfnOutput(self, "ClientUrl", value=f"{scheme}://{alb.load_balancer_dns_name}/")
        CfnOutput(self, "McpUrl", value=f"{scheme}://{alb.load_balancer_dns_name}/mcp")
        CfnOutput(self, "NovaActApiKeySecretName", value=nova_api_key.secret_name)
        CfnOutput(self, "McpApiTokenSecretName", value=mcp_token.secret_name)
