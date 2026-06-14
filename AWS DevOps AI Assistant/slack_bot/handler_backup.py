# handler.py

import json
import os
import hashlib
import hmac
import time
import logging

from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from agent.graph import get_agent
from memory.dynamodb_memory import DynamoDBMemory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

memory = DynamoDBMemory()
agent = get_agent()


@app.event("app_mention")
def handle_mention(event, say, client):
    """
    Triggered when user @mentions the bot.
    """

    question = event["text"]
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    user_id = event["user"]

    session_id = f"{channel}:{user_id}"

    # Slack requires quick response (<3 seconds)
    say(
        text="Thinking... :hourglass_flowing_sand:",
        thread_ts=thread_ts
    )

    # Load conversation history from DynamoDB
    history = memory.get_history(session_id)
    history_str = memory.format_history(history)

    try:
        # Run LangGraph agent
        result = agent.invoke(
            {
                "question": question,
                "user_id": user_id,
                "channel_id": channel,
                "messages": [],
                "context": "",
                "sources": [],
                "tool_results": [],
                "final_answer": None,
                "iteration": 0,
                "should_use_tools": False,
            }
        )

        answer = result["final_answer"]
        sources = result.get("sources", [])

    except Exception as e:
        logger.error(
            f"Agent error: {e}",
            exc_info=True
        )

        answer = f"Sorry, I encountered an error: {str(e)}"
        sources = []

    # Build Slack blocks
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": answer[:3000],
            },
        }
    ]

    if sources:
        src_text = "\n".join(
            f"• <{s}|Source>"
            for s in sources[:5]
            if s
        )

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Sources:*\n{src_text}",
                    }
                ],
            }
        )

    # Update Slack message
    client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text=answer[:3000],
        blocks=blocks,
    )

    # Save conversation to DynamoDB
    memory.save_turn(
        session_id,
        question,
        answer,
        sources,
    )


def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    """
    handler = SlackRequestHandler(app=app)
    return handler.handle(event, context)



def run_local_test():
    result = agent.invoke(
        {
            "question": "What is my name?",
            "user_id": "demo-user",
            "channel_id": "local",
            "messages": [],
            "history": "",
            "context": "",
            "sources": [],
            "tool_results": [],
            "final_answer": "",
            "iteration": 0,
            "should_use_tools": False,
        }
    )

    print("\n===== FINAL ANSWER =====\n")
    print(result["final_answer"])


if __name__ == "__main__":

    class MockSay:
        def __call__(self, text=None, thread_ts=None):
            print("\n[SAY]")
            print(text)

    class MockClient:
        def chat_update(self, **kwargs):
            print("\n[CHAT_UPDATE]")
            print(kwargs["text"])

    fake_event = {
        "text": "@devops-bot What is my name?",
        "channel": "TEST_CHANNEL",
        "user": "demo-user",
        "ts": "123456"
    }

    handle_mention(
        event=fake_event,
        say=MockSay(),
        client=MockClient()
    )