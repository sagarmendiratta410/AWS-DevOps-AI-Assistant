from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_logs as logs,
    aws_ssm as ssm,
)

from constructs import Construct


class LambdaStack(Stack):

    def __init__(
        self,
        scope: Construct,
        id: str,
        **kwargs,
    ):
        super().__init__(
            scope,
            id,
            **kwargs,
        )

        # ---------------------------------------------------
        # Lambda Execution Role
        # ---------------------------------------------------

        role = iam.Role(
            self,
            "AgentRole",
            assumed_by=iam.ServicePrincipal(
                "lambda.amazonaws.com"
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # ---------------------------------------------------
        # Bedrock Permissions
        # ---------------------------------------------------

        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )

        # ---------------------------------------------------
        # OpenSearch Permissions
        # ---------------------------------------------------

        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "aoss:APIAccessAll",
                ],
                resources=["*"],
            )
        )

        # ---------------------------------------------------
        # DynamoDB Permissions
        # ---------------------------------------------------

        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:*",
                ],
                resources=["*"],
            )
        )

        # ---------------------------------------------------
        # Slack Bot Lambda
        # ---------------------------------------------------

        self.slack_fn = _lambda.DockerImageFunction(
            self,
            "SlackBot",

            code=_lambda.DockerImageCode.from_image_asset(
                "."
            ),

            role=role,

            timeout=Duration.seconds(
                180
            ),

            memory_size=1024,

            environment={
                "AWS_REGION": self.region,

                "BEDROCK_LLM_MODEL_ID":
                    "amazon.nova-pro-v1:0",

                "BEDROCK_EMBED_MODEL_ID":
                    "amazon.titan-embed-text-v2:0",

                "OPENSEARCH_INDEX":
                    "devops-runbooks",

                # Sensitive values loaded
                # from Secrets Manager
                # at runtime
            },

            log_retention=
                logs.RetentionDays.ONE_MONTH,
        )