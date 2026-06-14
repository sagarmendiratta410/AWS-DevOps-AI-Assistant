import os

from langchain_aws import ChatBedrock
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from rag.chain import build_rag_chain
from agent.state import AgentState
from agent.tools import TOOLS, TOOLS_BY_NAME
from memory.dynamodb_memory import DynamoDBMemory

# ---------------------------------------------------------------------------
# LLM — bound with tools so it can emit tool_calls in its response
# ---------------------------------------------------------------------------
LLM = ChatBedrock(
    model_id=os.environ.get(
        "BEDROCK_LLM_MODEL_ID",
        "us.amazon.nova-pro-v1:0",   # cross-region inference profile for Nova
    ),
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    model_kwargs={
        "max_tokens": 4096,
        "temperature": 0.1,
    },
).bind_tools(TOOLS)

RAG_CHAIN = None
MEMORY = DynamoDBMemory()



def get_rag_chain():
    global RAG_CHAIN
    if RAG_CHAIN is None:
        RAG_CHAIN = build_rag_chain()
    return RAG_CHAIN



def load_memory_node(state: AgentState) -> dict:
    """
    Load conversation history from DynamoDB.
    """

    print(
        f"[NODE] load_memory_node | user={state['user_id']}"
    )

    try:
        history = MEMORY.get_history(
            state["user_id"]
        )

        history_str = MEMORY.format_history(
            history
        )

        print(
            f"[NODE] Loaded {len(history)} memory records"
        )

    except Exception as exc:
        print(
            f"[NODE] Memory load failed: {exc}"
        )

        history_str = ""

    return {
        "history": history_str
    }

# ============================================================================
# NODE 1: RETRIEVE CONTEXT
# ============================================================================
def retrieve_context_node(state: AgentState) -> dict:
    """Retrieve relevant docs from OpenSearch via RAG chain."""
    print(f"[NODE] retrieve_context_node | question={state['question']}")

    rag_chain = get_rag_chain()
    result = rag_chain.invoke({"question": state["question"]})

    context = result.get("context", "")
    sources = result.get("sources", [])

    print(f"[NODE] Retrieved {len(sources)} sources | context={len(context)} chars")

    return {
        "context": context,
        "sources": sources,
    }


# ============================================================================
# NODE 2: REASON AND PLAN
# Sends the question + context to the LLM with tools bound.
# If the LLM decides it needs a tool it emits tool_calls on the AIMessage.
# If it can answer from docs it just returns text with no tool_calls.
# ============================================================================
def reason_and_plan_node(state: AgentState) -> dict:
    """
    Ask the LLM what to do.
    The LLM either:
      - Returns a plain text response  → should_use_tools = False
      - Returns tool_calls on the msg  → should_use_tools = True
    """
    print("[NODE] reason_and_plan_node")

    system_msg = SystemMessage(content="""You are an expert AWS DevOps assistant.

You have access to company documentation AND real-time tools.

Decision rules:
1. If the question asks to CHECK, QUERY, FETCH, LIST, or SEARCH live data
   (logs, deployments, incidents, PRs) -> call the appropriate tool(s).
2. If the question is conceptual / how-to and the retrieved docs answer it
   -> answer directly without tools.
3. If docs are incomplete and live data would help -> use tools.

Available tools:
- query_cloudwatch_logs   : search live CloudWatch log groups for errors/patterns
- list_recent_deployments : list recent ECS/EKS deployment events
- search_jira_incidents   : search past Jira incidents by keyword
- get_github_pr_info      : fetch GitHub PR details
- send_slack_alert        : send an alert to a Slack channel

Always prefer tools for operational/live queries.""")

    human_msg = HumanMessage(
        content=f"""
    Conversation History:
    {state.get('history', '')}

    Current Question:
    {state['question']}

    Retrieved Documentation:
    {state['context'][:3000]}

    Answer the question. Use tools if you need live data."""
    )

    # Pass full conversation history + new messages to the LLM
    invoke_messages = state.get("messages", []) + [system_msg, human_msg]
    response: AIMessage = LLM.invoke(invoke_messages)

    # Detect whether the LLM wants to call tools — rely on actual tool_calls,
    # NOT string parsing. This is the correct LangChain pattern.
    has_tool_calls = bool(getattr(response, "tool_calls", None))
    should_use_tools = has_tool_calls

    print(f"[NODE] should_use_tools={should_use_tools} | "
          f"tool_calls={[tc['name'] for tc in (response.tool_calls or [])]}")

    return {
        "messages": [system_msg, human_msg, response],
        "should_use_tools": should_use_tools,
    }


# ============================================================================
# NODE 3: EXECUTE TOOLS
# Reads tool_calls from the last AIMessage, runs each tool, appends
# ToolMessage results so the LLM can reference them in synthesise_answer_node.
# ============================================================================
def execute_tools_node(state: AgentState) -> dict:
    """Execute every tool_call in the last AIMessage."""
    print("[NODE] execute_tools_node")

    messages = state.get("messages", [])

    # Find the most recent AIMessage that has tool_calls
    last_ai_msg = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage)),
        None,
    )

    if not last_ai_msg or not getattr(last_ai_msg, "tool_calls", None):
        print("[NODE] No tool calls found — skipping")
        return {"tool_results": state.get("tool_results", [])}

    tool_results = list(state.get("tool_results", []))
    new_tool_messages: list = []

    for tc in last_ai_msg.tool_calls:
        tool_name = tc["name"]
        tool_input = tc["args"]
        tool_call_id = tc["id"]

        print(f"[NODE] Calling tool: {tool_name}({tool_input})")

        tool_fn = TOOLS_BY_NAME.get(tool_name)
        if tool_fn is None:
            output = f"Tool '{tool_name}' not found."
            status = "error"
        else:
            try:
                output = tool_fn.invoke(tool_input)
                status = "success"
            except Exception as exc:
                output = f"Tool error: {exc}"
                status = "error"

        print(f"[NODE] {tool_name} -> status={status} | preview={str(output)[:120]}")

        tool_results.append({
            "tool": tool_name,
            "result": output,
            "status": status,
        })

        # ToolMessage feeds the result back into the conversation so the LLM
        # can reference it when synthesising the final answer.
        new_tool_messages.append(
            ToolMessage(
                content=str(output),
                tool_call_id=tool_call_id,
                name=tool_name,
            )
        )

    print(f"[NODE] Executed {len(new_tool_messages)} tools")

    return {
        "tool_results": tool_results,
        "messages": new_tool_messages,   # operator.add reducer appends these
    }


# ============================================================================
# NODE 4: SYNTHESISE ANSWER
# The LLM now has the full conversation (docs + tool results) and writes
# a final, cited, actionable answer.
# ============================================================================
def synthesise_answer_node(state: AgentState) -> dict:
    """Produce the final answer using docs + tool results."""
    print("[NODE] synthesise_answer_node")

    tool_results_text = ""
    for tr in state.get("tool_results", []):
        tool_results_text += f"\n### {tr['tool']} (status={tr['status']})\n{tr['result']}\n"

    final_msg = HumanMessage(
        content=f"""You are a DevOps expert. Write a clear, actionable answer.

Original question: {state['question']}

--- Retrieved Documentation ---
{state['context']}

--- Tool Results ---
{tool_results_text or 'No tools were called.'}

Instructions:
- Cite source URLs or tool names for every key fact
- Put shell/kubectl/python commands in code blocks
- Be concise and practical
- If tool results contain the answer, lead with that
"""
    )

    invoke_messages = state.get("messages", []) + [final_msg]
    response: AIMessage = LLM.invoke(invoke_messages)

    final_answer = response.content if hasattr(response, "content") else str(response)
    print(f"[NODE] Final answer length: {len(final_answer)} chars")

    return {
        "final_answer": final_answer,
        "iteration": state.get("iteration", 0) + 1,
        "messages": [final_msg, response],
    }


def save_memory_node(state: AgentState) -> dict:
    """
    Save current interaction to DynamoDB.
    """

    print("[NODE] save_memory_node")

    try:

        MEMORY.save_turn(
            session_id=state["user_id"],
            question=state["question"],
            answer=state["final_answer"],
            sources=state.get(
                "sources",
                [],
            ),
        )

        print(
            "[NODE] Memory saved"
        )

    except Exception as exc:

        print(
            f"[NODE] Memory save failed: {exc}"
        )

    return {}