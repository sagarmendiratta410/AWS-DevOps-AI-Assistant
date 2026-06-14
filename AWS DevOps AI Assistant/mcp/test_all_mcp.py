from mcp.aws_mcp import AWSMCPClient
from mcp.github_mcp import GitHubMCPClient
from mcp.slack_mcp import SlackMCPClient
from mcp.jira_mcp import JiraMCPClient
from dotenv import load_dotenv

load_dotenv()


aws_client = AWSMCPClient()
github_client = GitHubMCPClient()
slack_client = SlackMCPClient()
jira_client = JiraMCPClient()


aws_result1 = aws_client.query_logs(
    log_group="/aws/lambda/api-service",
    filter_pattern="ERROR",
    hours_back=20
)

aws_result2 = aws_client.run_insights_query(
    "/aws/lambda/api-service",
    """
    fields @timestamp, @message
    | sort @timestamp desc
    | limit 20
    """,
    hours_back=20,
)

print("\n" + "=" * 80)
print("TESTING JIRA MCP")
print("=" * 80)
jira_result = jira_client.search_incidents(
    keyword="timeout"
)

print("\nRESULT:\n")
print(jira_result)


print("\n" + "=" * 80)
print("TESTING AWS MCP")
print("=" * 80)

print("\nRESULT:")
print(aws_result2)
print(aws_result1)


print("\n" + "=" * 80)
print("TESTING GITHUB  MCP")
print("=" * 80)
print(
    github_client.get_recent_commits(
        "infra"
    )
)

print("\n")
print("=" * 80)
print("TESTING SLACK MCP")
print("=" * 80)

slack_client.post_message(
    channel="#devops-alerts",
    text="Hello from DevOps AI Assistant"
)

slack_client.post_incident_alert(
    channel="#devops-alerts",
    title="API Service Failure",
    description=(
        "CloudWatch detected "
        "multiple ERROR events."
    ),
    severity="P1",
    service="api-service",
)