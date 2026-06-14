# test_slack.py

from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bot.handler import app
import os
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    SocketModeHandler(
        app,
        os.environ["SLACK_APP_TOKEN"]
    ).start()