# slack_bot/handler.py

import os
import re
import sys
import logging
import warnings
from langchain_core._api.deprecation import LangChainPendingDeprecationWarning
# ─────────────────────────────────────────────────────────────────────────────
# Force immediate terminal output (no buffering)
# ─────────────────────────────────────────────────────────────────────────────
sys.stdout.reconfigure(line_buffering=True)

# ─────────────────────────────────────────────────────────────────────────────
# Suppress all warnings and noisy library logs
# ─────────────────────────────────────────────────────────────────────────────
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)

for lib in [
    "memory.dynamodb_memory",
    "langchain_aws",
    "opensearch",
    "botocore",
    "slack_bolt",
    "urllib3",
    "langgraph",
    "httpx",
    "httpcore",
]:
    logging.getLogger(lib).setLevel(logging.WARNING)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────────────────────
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from agent.graph import get_agent
from memory.dynamodb_memory import DynamoDBMemory


# ─────────────────────────────────────────────────────────────────────────────
# Logger Helpers
# ─────────────────────────────────────────────────────────────────────────────

STEP = 0


def step(msg: str, file: str = "", func: str = "", detail: str = ""):
    global STEP
    STEP += 1
    print(f"\n[STEP {STEP:02d}] {msg}", flush=True)
    if file:   print(f"         📁 file     : {file}", flush=True)
    if func:   print(f"         ⚙️  function : {func}", flush=True)
    if detail: print(f"         ↳ {detail}", flush=True)


def reset_steps():
    global STEP
    STEP = 0


def log_section(title: str):
    width = max(len(title) + 4, 60)
    print(f"\n{'═' * width}", flush=True)
    print(f"  {title}", flush=True)
    print(f"{'═' * width}", flush=True)


def log_info(label: str, value: str):
    print(f"         {label:<18}: {value}", flush=True)


def log_ok(msg: str):
    print(f"         ✅ {msg}", flush=True)


def log_err(msg: str):
    print(f"         ❌ {msg}", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP — Runs once when bot starts
# ─────────────────────────────────────────────────────────────────────────────

log_section("DevOps AI Assistant — Starting Up")
print(flush=True)
print("  Everything loads NOW at startup (not when you ask questions).", flush=True)
print("  This makes responses fast. Here is what is loading:", flush=True)
print(flush=True)

# ── Startup Step 1 ────────────────────────────────────────────────────────────
step(
    msg    = "Loading Slack App",
    file   = "slack_bolt  (Slack pip library)",
    func   = "App.__init__()",
    detail = "Authenticates with Slack using SLACK_BOT_TOKEN"
)
app = App(token=os.environ["SLACK_BOT_TOKEN"])
log_ok("Slack App authenticated and ready")

# ── Startup Step 2 ────────────────────────────────────────────────────────────
step(
    msg    = "Connecting to DynamoDB Memory",
    file   = "memory/dynamodb_memory.py",
    func   = "DynamoDBMemory.__init__()",
    detail = "Connects to devops-ai-memory and devops-ai-incidents tables"
)
memory = DynamoDBMemory()
log_ok("DynamoDB connected — memory tables ready")
log_info("memory table",    os.environ.get("DYNAMODB_MEMORY_TABLE",    "devops-ai-memory"))
log_info("incidents table", os.environ.get("DYNAMODB_INCIDENTS_TABLE", "devops-ai-incidents"))

# ── Startup Step 3 ────────────────────────────────────────────────────────────
step(
    msg    = "Building LangGraph Agent",
    file   = "agent/graph.py",
    func   = "build_agent_graph()",
    detail = "Compiles the full AI pipeline with all nodes and edges"
)
print("""
         Node pipeline being compiled:
         ┌────────────────────────────────────────────────────┐
         │  [1] load_memory_node                              │
         │       📁 agent/nodes.py → load_memory_node()       │
         │       ↳ Loads past conversations from DynamoDB     │
         │                      ↓                             │
         │  [2] retrieve_context_node                         │
         │       📁 agent/nodes.py → retrieve_context_node()  │
         │       ↳ Searches OpenSearch with hybrid search     │
         │                      ↓                             │
         │  [3] reason_and_plan_node                          │
         │       📁 agent/nodes.py → reason_and_plan_node()   │
         │       ↳ Nova decides: answer now or use tools?     │
         │                      ↓                             │
         │  [4] execute_tools_node                            │
         │       📁 agent/nodes.py → execute_tools_node()     │
         │       ↳ Runs CloudWatch / Jira / GitHub tools      │
         │                      ↓                             │
         │  [5] synthesise_answer_node                        │
         │       📁 agent/nodes.py → synthesise_answer_node() │
         │       ↳ Nova writes the final answer               │
         │                      ↓                             │
         │  [6] save_memory_node                              │
         │       📁 agent/nodes.py → save_memory_node()       │
         │       ↳ Saves Q&A to DynamoDB for next time        │
         └────────────────────────────────────────────────────┘
""", flush=True)

agent = get_agent()
log_ok("LangGraph agent compiled successfully")
log_info("model",  os.environ.get("BEDROCK_LLM_MODEL_ID", "us.amazon.nova-pro-v1:0"))
log_info("region", os.environ.get("AWS_REGION",           "us-east-1"))
log_info("index",  os.environ.get("OPENSEARCH_INDEX",     "devops-runbooks"))

# ── Startup Step 4 ────────────────────────────────────────────────────────────
step(
    msg    = "Registering Slack Event Handlers",
    file   = "slack_bot/handler.py",
    func   = "@app.event('app_mention')",
    detail = "Bot will respond whenever someone @mentions it"
)
log_ok("app_mention handler registered")
print("""
         When you type:  @DevOps AI Assistant what is terraform?
         Slack sends:    WebSocket event → this handler
         Bot runs:       All 6 nodes above → posts answer
""", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def clean_question(text: str) -> str:
    """Remove Slack @mention tags like <@U0B82M8JUF9> from question."""
    text = re.sub(r'<@[A-Z0-9]+>', '', text)
    return ' '.join(text.split()).strip()


def build_slack_blocks(answer: str, sources: list) -> list:
    """Build Slack Block Kit message with answer and source links."""
    blocks = [{
        "type": "section",
        "text": {"type": "mrkdwn", "text": answer[:3000]},
    }]

    unique_sources = list(dict.fromkeys(s for s in sources if s))[:5]

    if unique_sources:
        src_lines = "\n".join(
            f"• <{s}|Source {i+1}>"
            for i, s in enumerate(unique_sources)
        )
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"*Sources:*\n{src_lines}"
            }],
        })

    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# Main Event Handler — runs every time someone @mentions the bot
# ─────────────────────────────────────────────────────────────────────────────

@app.event("app_mention")
def handle_mention(event, say, client):
    """
    Triggered every time someone @mentions the bot in Slack.

    STEP 01 → Slack event received
    STEP 02 → Question cleaned and extracted
    STEP 03 → Thinking message sent to Slack
    STEP 04 → Conversation history loaded from DynamoDB
    STEP 05 → LangGraph Agent executed
    STEP 06 → Answer posted to Slack
    STEP 07 → Conversation saved to DynamoDB
    """

    reset_steps()

    log_section("New Question Received from Slack")

    # ── STEP 01 ───────────────────────────────────────────────────────────────
    step(
        msg    = "Slack event received",
        file   = "slack_bot/handler.py",
        func   = "handle_mention(event, say, client)",
        detail = "app_mention event pushed via WebSocket from Slack"
    )
    log_info("user",     event.get('user',    'unknown'))
    log_info("channel",  event.get('channel', 'unknown'))
    log_info("raw text", event.get('text',    '')[:80])

    # ── STEP 02 ───────────────────────────────────────────────────────────────
    raw_text   = event.get("text", "")
    question   = clean_question(raw_text)
    user_id    = event.get("user",      "unknown")
    channel_id = event.get("channel",   "")
    thread_ts  = event.get("thread_ts", event.get("ts", ""))
    session_id = f"{channel_id}:{user_id}"

    step(
        msg    = "Question cleaned and extracted",
        file   = "slack_bot/handler.py",
        func   = "clean_question(text)",
        detail = "Strips <@mention> tags so Nova gets clean question text"
    )
    log_info("raw",        raw_text[:80])
    log_info("cleaned",    question)
    log_info("session_id", session_id)
    log_info("thread_ts",  thread_ts)

    # ── STEP 03 ───────────────────────────────────────────────────────────────
    step(
        msg    = "Sending 'Thinking' message to Slack",
        file   = "slack_bot/handler.py",
        func   = "say(text=..., thread_ts=...)",
        detail = "User sees this instantly while processing happens in background"
    )
    say(text="Thinking... :hourglass_flowing_sand:", thread_ts=thread_ts)
    log_ok("'Thinking...' delivered to Slack thread")

    # ── STEP 04 ───────────────────────────────────────────────────────────────
    history     = memory.get_history(session_id)
    history_str = memory.format_history(history)

    step(
        msg    = f"Conversation history loaded — {len(history)} records",
        file   = "memory/dynamodb_memory.py",
        func   = "DynamoDBMemory.get_history(session_id)",
        detail = "Past Q&A loaded so Nova remembers previous conversation context"
    )
    log_info("session",  session_id)
    log_info("records",  str(len(history)))
    log_info("table",    os.environ.get("DYNAMODB_MEMORY_TABLE", "devops-ai-memory"))

    if history:
        log_info("oldest Q", history[0].get('question', '')[:60])
        log_info("latest Q", history[-1].get('question', '')[:60])
    else:
        print("         ↳ No history yet — this is a fresh conversation", flush=True)

    # ── STEP 05 ───────────────────────────────────────────────────────────────
    step(
        msg    = "Running LangGraph Agent",
        file   = "agent/graph.py",
        func   = "get_agent().invoke(state)",
        detail = "Runs all 6 nodes: load_memory → retrieve → reason → tools → synthesise → save"
    )
    print("""
         Watch the sub-logs below — each node prints its own output:
         [NODE] load_memory_node        📁 agent/nodes.py
         [HYBRID] RETRIEVAL START       📁 rag/retriever.py
         [RERANK] START                 📁 rag/reranker.py
         [NODE] reason_and_plan_node    📁 agent/nodes.py
         [TOOL]  search_jira_incidents  📁 agent/tools.py
         [NODE] synthesise_answer_node  📁 agent/nodes.py
         [NODE] save_memory_node        📁 agent/nodes.py
    """, flush=True)

    try:
        result = agent.invoke({
            "question":         question,
            "user_id":          user_id,
            "channel_id":       channel_id,
            "messages":         [],
            "context":          "",
            "sources":          [],
            "tool_results":     [],
            "final_answer":     None,
            "iteration":        0,
            "should_use_tools": False,
        })

        answer  = result.get("final_answer", "Sorry, I could not find an answer.")
        sources = result.get("sources", [])

        print("\n         ── Agent Execution Summary ─────────────────────────", flush=True)
        log_ok("LangGraph completed successfully")
        log_info("📁 graph.py",   "all 6 nodes executed")
        log_info("answer length", f"{len(answer)} chars")
        log_info("sources found", str(len(sources)))
        log_info("iterations",    str(result.get('iteration', 0)))
        log_info("tool results",  str(len(result.get('tool_results', []))))
        print("         ─────────────────────────────────────────────────────", flush=True)
        print(f"\n         Answer preview:", flush=True)
        print(f"         {answer[:200]}...", flush=True)
        print("         ─────────────────────────────────────────────────────", flush=True)

    except Exception as e:
        logger.error(f"[AGENT ERROR] {e}", exc_info=True)
        answer  = f"Sorry, I encountered an error: {str(e)[:300]}"
        sources = []
        log_err(f"Agent failed: {e}")

    # ── STEP 06 ───────────────────────────────────────────────────────────────
    step(
        msg    = "Posting final answer to Slack",
        file   = "slack_bot/handler.py",
        func   = "client.chat_postMessage(channel, thread_ts, blocks)",
        detail = "Sends formatted answer with clickable source links to the thread"
    )
    blocks = build_slack_blocks(answer, sources)
    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=answer[:3000],
        blocks=blocks,
    )
    log_ok("Answer delivered to Slack thread")
    log_info("channel",       channel_id)
    log_info("thread",        thread_ts)
    log_info("blocks sent",   str(len(blocks)))
    log_info("sources cited", str(len([s for s in sources if s])))

    # ── STEP 07 ───────────────────────────────────────────────────────────────
    step(
        msg    = "Saving conversation to DynamoDB",
        file   = "memory/dynamodb_memory.py",
        func   = "DynamoDBMemory.save_turn(session_id, question, answer, sources)",
        detail = "Stores Q&A with 7-day TTL so bot remembers for future questions"
    )
    memory.save_turn(
        session_id=session_id,
        question=question,
        answer=answer,
        sources=sources,
    )
    updated = memory.get_history(session_id)
    log_ok("Conversation saved successfully")
    log_info("session",       session_id)
    log_info("table",         os.environ.get("DYNAMODB_MEMORY_TABLE", "devops-ai-memory"))
    log_info("total records", str(len(updated)))
    log_info("expires",       "7 days from now (auto TTL)")

    log_section("✅ COMPLETE — Question answered and saved")
    print(f"  question : {question[:70]}", flush=True)
    print(f"  answer   : {answer[:100]}...", flush=True)
    print(f"  memory   : {len(updated)} total records in DynamoDB", flush=True)
    print(flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Lambda Entry Point — used when deploying to production AWS Lambda
# ─────────────────────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    """AWS Lambda entry point for production deployment."""
    from slack_bolt.adapter.aws_lambda import SlackRequestHandler
    handler = SlackRequestHandler(app=app)
    return handler.handle(event, context)


# ─────────────────────────────────────────────────────────────────────────────
# Local Run via Socket Mode
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    socket_handler = SocketModeHandler(
        app=app,
        app_token=os.environ["SLACK_APP_TOKEN"],
    )

    log_section("✅ Bot is LIVE — Waiting for Slack messages")
    print("""
  How to use:
  1. Go to Slack → open #devops-alerts channel
  2. Type: @DevOps AI Assistant what is terraform?
  3. Watch this terminal — STEP 01 to STEP 07 will appear
  4. Each step shows exactly which file and function ran

  Tip: If something breaks, the step number tells you exactly
       which file to check and which function failed.
    """, flush=True)

    socket_handler.start()