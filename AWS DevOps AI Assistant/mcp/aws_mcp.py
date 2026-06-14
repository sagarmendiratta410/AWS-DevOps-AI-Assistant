import json
import logging
import os
import time

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


class AWSMCPClient:
    """
    Production-ready CloudWatch MCP Client.

    Features:
    - Retry support
    - Better logging
    - Pagination
    - Configurable limits
    - Query timeout handling
    """

    def __init__(self):

        region = os.environ.get(
            "AWS_REGION",
            "us-east-1",
        )

        logger.info(
            f"Initializing AWSMCPClient "
            f"(region={region})"
        )

        retry_config = Config(
            retries={
                "max_attempts": 10,
                "mode": "standard",
            }
        )

        self.logs = boto3.client(
            "logs",
            region_name=region,
            config=retry_config,
        )

    # =====================================================
    # FILTER LOG EVENTS
    # =====================================================

    def query_logs(
        self,
        log_group: str,
        filter_pattern: str,
        minutes_back: int = 60,
        max_events: int = 100,
    ) -> str:

        print("\n" + "=" * 80)
        print("[AWS MCP] QUERY LOGS")
        print(f"Log Group     : {log_group}")
        print(f"Filter Pattern: {filter_pattern}")
        print(f"Minutes Back  : {minutes_back}")
        print("=" * 80)

        start_time = int(
            (time.time() - minutes_back * 60) * 1000
        )

        end_time = int(
            time.time() * 1000
        )

        events = []
        next_token = None

        try:

            while len(events) < max_events:

                kwargs = {
                    "logGroupName": log_group,
                    "filterPattern": filter_pattern,
                    "startTime": start_time,
                    "endTime": end_time,
                    "limit": min(
                        100,
                        max_events - len(events),
                    ),
                }

                if next_token:
                    kwargs["nextToken"] = next_token

                response = self.logs.filter_log_events(
                    **kwargs
                )

                events.extend(
                    response.get("events", [])
                )

                next_token = response.get(
                    "nextToken"
                )

                if not next_token:
                    break

            print(
                f"[AWS MCP] Retrieved "
                f"{len(events)} events"
            )

            if not events:

                return (
                    f'No events found matching '
                    f'"{filter_pattern}" '
                    f'in last {minutes_back} minutes'
                )

            formatted = []

            for event in events[:20]:

                ts = event["timestamp"]

                msg = event["message"].strip()

                formatted.append(
                    f"[{ts}] {msg}"
                )

            return (
                f"Found {len(events)} events\n\n"
                + "\n".join(formatted)
            )

        except self.logs.exceptions.ResourceNotFoundException:

            logger.error(
                f"Log group not found: {log_group}"
            )

            return (
                f"Log group not found: "
                f"{log_group}"
            )

        except Exception as e:

            logger.exception(
                "CloudWatch query failed"
            )

            return (
                f"CloudWatch query failed: {e}"
            )

    # =====================================================
    # INSIGHTS QUERY
    # =====================================================

    def run_insights_query(
        self,
        log_group: str,
        query_string: str,
        minutes_back: int = 1,
        timeout_seconds: int = 60,
    ) -> str:

        print("\n" + "=" * 80)
        print("[AWS MCP] INSIGHTS QUERY")
        print(f"Log Group : {log_group}")
        print(f"Minutes Back: {minutes_back}")
        print("=" * 80)

        start_time = int(
            time.time() - minutes_back * 60
        )

        end_time = int(
            time.time()
        )

        try:

            response = (
                self.logs.start_query(
                    logGroupName=log_group,
                    startTime=start_time,
                    endTime=end_time,
                    queryString=query_string,
                )
            )

            query_id = response["queryId"]

            print(
                f"[AWS MCP] Query ID: "
                f"{query_id}"
            )

            deadline = (
                time.time()
                + timeout_seconds
            )

            result = None

            while time.time() < deadline:

                result = (
                    self.logs.get_query_results(
                        queryId=query_id
                    )
                )

                status = result["status"]

                print(
                    f"[AWS MCP] Status: "
                    f"{status}"
                )

                if status in (
                    "Complete",
                    "Failed",
                    "Cancelled",
                    "Timeout",
                ):
                    break

                time.sleep(2)

            if not result:

                return (
                    "No query result returned"
                )

            if result["status"] != "Complete":

                return (
                    f"Query ended with "
                    f"status={result['status']}"
                )

            rows = result.get(
                "results",
                []
            )

            print(
                f"[AWS MCP] Rows returned: "
                f"{len(rows)}"
            )

            return json.dumps(
                rows[:20],
                indent=2,
            )

        except Exception as e:

            logger.exception(
                "Insights query failed"
            )

            return (
                f"CloudWatch Insights error: "
                f"{e}"
            )