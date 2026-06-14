from agent.graph import get_agent

agent = get_agent()

result = agent.invoke(
    {
        "question": "Check if any ERROR messages are there in api-service in last 28 mins",
        "messages": [],
        "context": "",
        "sources": [],
        "tool_results": [],
        "final_answer": None,
        "user_id": "test",
        "channel_id": "test",
        "iteration": 0,
        "should_use_tools": False,
    }
)

print("\nFINAL ANSWER")
print(result["final_answer"])