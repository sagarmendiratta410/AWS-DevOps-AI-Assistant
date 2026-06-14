from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

import logging
import os

logger = logging.getLogger(__name__)


class SlackMCPClient:

    def __init__(self):

        self.client = WebClient(
            token=os.environ["SLACK_BOT_TOKEN"]
        )

        print("\n" + "=" * 80)
        print("[SLACK MCP] Initialized")
        print("=" * 80)

    # =====================================================
    # BASIC MESSAGE
    # =====================================================

    def post_message(
        self,
        channel: str,
        text: str,
    ) -> str:

        try:

            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
            )

            print(
                f"[SLACK MCP] Message sent "
                f"to {channel}"
            )

            return response["ts"]

        except SlackApiError as e:

            logger.exception(
                "Slack message failed"
            )

            return (
                f"Slack error: "
                f"{e.response['error']}"
            )

    # =====================================================
    # INCIDENT CARD UI
    # =====================================================

    def post_incident_alert(
        self,
        channel: str,
        title: str,
        description: str,
        severity: str = "P2",
        service: str = "unknown",
        environment: str = "production",
    ) -> str:

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": (
                        f"🚨 {severity} Incident"
                    ),
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text":
                        f"*Service:*\n{service}",
                    },
                    {
                        "type": "mrkdwn",
                        "text":
                        f"*Environment:*\n{environment}",
                    },
                    {
                        "type": "mrkdwn",
                        "text":
                        f"*Severity:*\n{severity}",
                    },
                    {
                        "type": "mrkdwn",
                        "text":
                        "*Status:*\nOpen",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text":
                    f"*Title*\n{title}\n\n"
                    f"*Description*\n"
                    f"{description}",
                },
            },
            {
                "type": "divider",
            },
        ]

        try:

            response = (
                self.client.chat_postMessage(
                    channel=channel,
                    text=title,
                    blocks=blocks,
                )
            )

            print(
                "[SLACK MCP] Incident "
                "alert posted"
            )

            return response["ts"]

        except SlackApiError as e:

            logger.exception(
                "Slack incident failed"
            )

            return (
                f"Slack error: "
                f"{e.response['error']}"
            )