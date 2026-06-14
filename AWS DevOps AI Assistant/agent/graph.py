from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    load_memory_node,
    retrieve_context_node,
    reason_and_plan_node,
    execute_tools_node,
    synthesise_answer_node,
    save_memory_node,
)
from agent.state import AgentState


def build_agent_graph():
    """
    Build the LangGraph agent graph.
    
    Flow:
    START → retrieve → reason → (conditional: tools or synthesise) 
         → tools → (conditional: loop back or synthesise)
         → synthesise → END
    """
    print("[GRAPH] Building LangGraph agent")

    try:
        graph = StateGraph(AgentState)

        # Add nodes
        print("[GRAPH] Adding nodes...")
        graph.add_node("load_memory", load_memory_node)
        graph.add_node("retrieve", retrieve_context_node)
        graph.add_node("reason", reason_and_plan_node)
        graph.add_node("tools", execute_tools_node)
        graph.add_node("synthesise", synthesise_answer_node)
        graph.add_node("save_memory", save_memory_node)

        # Define edges/transitions
        print("[GRAPH] Adding edges...")
        
        # Start at retrieve
        graph.add_edge(START, "load_memory")
        graph.add_edge("load_memory", "retrieve")
        
        # Retrieve always leads to reason
        graph.add_edge("retrieve", "reason")

        # After reason: decide if tools needed
        graph.add_conditional_edges(
            "reason",
            lambda state: (
                "tools"
                if state["should_use_tools"]
                else "synthesise"
            ),
            {
                "tools": "tools",
                "synthesise": "synthesise",
            },
        )

        # After tools: loop back to reason (max 3 iterations) or go to synthesise
        graph.add_conditional_edges(
            "tools",
            lambda state: (
                "reason"
                if state["iteration"] < 3
                else "synthesise"
            ),
            {
                "reason": "reason",
                "synthesise": "synthesise",
            },
        )

        # Synthesise is the final step
        graph.add_edge("synthesise", "save_memory")
        graph.add_edge("save_memory", END)

        print("[GRAPH] Graph structure complete")
        compiled_graph = graph.compile()
        print("[GRAPH] Graph compiled successfully")
        return compiled_graph

    except Exception as e:
        print(f"[GRAPH] ERROR building graph: {e}")
        raise


# Singleton pattern: cache the agent so we don't rebuild it
_AGENT = None


def get_agent():
    """
    Get or create the agent graph (singleton).
    
    Returns:
        Compiled LangGraph agent ready to invoke
    """
    global _AGENT

    if _AGENT is None:
        print("[GRAPH] Initializing singleton agent")
        _AGENT = build_agent_graph()

    return _AGENT