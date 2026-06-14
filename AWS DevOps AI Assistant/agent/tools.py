import json
import os
import time

import boto3
from langchain_core.tools import tool

from mcp.aws_mcp import AWSMCPClient
from mcp.github_mcp import GitHubMCPClient
from mcp.jira_mcp import JiraMCPClient
from mcp.slack_mcp import SlackMCPClient


@tool
def query_cloudwatch_logs(
    log_group: str,
    filter_pattern: str,
    minutes_back: int = 60,
) -> str:
    """
    Query CloudWatch Logs for error patterns and debugging.

    Use this when you need to:
    - Find error messages in application logs
    - Debug recent failures or exceptions
    - Check for specific error patterns (ERROR, Exception, 5xx, etc)
    - Investigate deployment issues

    Args:
        log_group: CloudWatch log group name
            Examples: /aws/lambda/my-function, /aws/ecs/my-service, /aws/lambda/api-service
        filter_pattern: Filter pattern string
            Examples: "ERROR", "Exception", "5xx"
        minutes_back: How far back to search in minutes (default 60)

    Returns:
        JSON formatted log entries matching the filter pattern
    """
    print(
        f"[TOOL] query_cloudwatch_logs | "
        f"log_group={log_group}, filter={filter_pattern}, minutes_back={minutes_back}"
    )
    try:
        client = AWSMCPClient()
        result = client.query_logs(log_group, filter_pattern, minutes_back)
        print("[TOOL] query_cloudwatch_logs completed")
        return result
    except Exception as e:
        error_msg = f"Error querying CloudWatch logs: {str(e)}"
        print(f"[TOOL] query_cloudwatch_logs ERROR: {error_msg}")
        return error_msg


@tool
def get_github_pr_info(repo: str, pr_number: int) -> str:
    """
    Get detailed information about a GitHub pull request.

    Use this when you need to:
    - Check if a PR has been merged or is still open
    - See what changes were made in a deployment
    - Find PR author, reviewers, and merge status

    Args:
        repo: Repository name without org prefix
            Examples: "infra", "platform"
        pr_number: Pull request number
            Example: 42

    Returns:
        PR details including status, author, changes, and merge status
    """
    print(f"[TOOL] get_github_pr_info | repo={repo}, pr_number={pr_number}")
    try:
        client = GitHubMCPClient()
        result = client.get_pr(repo, pr_number)
        print("[TOOL] get_github_pr_info completed")
        return result
    except Exception as e:
        error_msg = f"Error fetching GitHub PR: {str(e)}"
        print(f"[TOOL] get_github_pr_info ERROR: {error_msg}")
        return error_msg


@tool
def list_recent_deployments(service: str, minutes_back: int = 60) -> str:
    """
    List recent ECS/EKS deployments and service updates.

    Use this when you need to:
    - See what services were recently deployed
    - Check deployment timeline and history
    - Find which version is currently running
    - Verify if a rollback has occurred

    Args:
        service: Service name to filter by
            Examples: "my-api", "devops-bot"
        minutes_back: Minutes back to search (default 1440)

    Returns:
        List of recent deployment events for the service
    """
    print(f"[TOOL] list_recent_deployments | service={service}, minutes_back={minutes_back}")
    try:
        logs = boto3.client("logs", region_name=os.environ["AWS_REGION"])
        response = logs.filter_log_events(
            logGroupName="/aws/cloudtrail/devops",
            filterPattern=(
                f'{{$.eventName = "UpdateService" && '
                f'$.requestParameters.service = "{service}"}}'
            ),
            startTime=int((time.time() - minutes_back * 60) * 1000),
        )
        events = [event["message"] for event in response.get("events", [])]
        print(f"[TOOL] Found {len(events)} deployment events for service={service}")
        return (
            json.dumps(events[:10])
            if events
            else f"No deployments found for {service} in the last {minutes_back} minutes"
        )
    except Exception as e:
        error_msg = f"Error listing deployments: {str(e)}"
        print(f"[TOOL] list_recent_deployments ERROR: {error_msg}")
        return error_msg


@tool
def search_jira_incidents(error_code: str) -> str:
    """
    Search Jira for past incidents matching a keyword or error code.

    Use this when you need to:
    - Find similar past incidents
    - Check if an error has occurred before
    - Look up resolution steps from previous incidents

    Args:
        error_code: Error code or search keyword
            Examples: "timeout", "CrashLoopBackOff", "DB-502"

    Returns:
        Matching Jira issues with status and description
    """
    print(f"[TOOL] search_jira_incidents | error_code={error_code}")
    try:
        client = JiraMCPClient()
        result = client.search_incidents(keyword=error_code)
        print("[TOOL] search_jira_incidents completed")
        return result
    except Exception as e:
        error_msg = f"Error searching Jira incidents: {str(e)}"
        print(f"[TOOL] search_jira_incidents ERROR: {error_msg}")
        return error_msg


@tool
def send_slack_alert(
    channel: str,
    title: str,
    description: str,
    severity: str = "P2",
) -> str:
    """
    Send an incident alert to a Slack channel.

    Use this when you need to:
    - Notify engineers about incidents
    - Send production alerts or escalations
    - Inform teams about deployment issues

    Args:
        channel: Slack channel name
            Example: "#devops"
        title: Short incident title
            Example: "API Service Down"
        description: Detailed description of the incident
        severity: One of P1 (Critical), P2 (High), P3 (Medium)

    Returns:
        Success or failure message
    """
    print(f"[TOOL] send_slack_alert | channel={channel}, severity={severity}")
    try:
        client = SlackMCPClient()
        result = client.post_incident_alert(
            channel=channel,
            title=title,
            description=description,
            severity=severity,
        )
        print("[TOOL] send_slack_alert completed")
        return result if result else "Slack alert sent successfully"
    except Exception as e:
        error_msg = f"Error sending Slack alert: {str(e)}"
        print(f"[TOOL] send_slack_alert ERROR: {error_msg}")
        return error_msg


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
TOOLS = [
    query_cloudwatch_logs,
    get_github_pr_info,
    list_recent_deployments,
    search_jira_incidents,
    send_slack_alert,
]

# Dict lookup used by execute_tools_node to call tools by name
TOOLS_BY_NAME = {t.name: t for t in TOOLS}
