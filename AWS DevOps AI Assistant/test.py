from agent.graph import get_agent

agent = get_agent()

print("=" * 50)

agent.invoke(
    {
        "question": "My name is Sagar",
        "user_id": "demo-user",
        "channel_id": "local",
        "messages": [],
        "context": "",
        "history": "",
        "sources": [],
        "tool_results": [],
        "final_answer": "",
        "iteration": 0,
        "should_use_tools": False,
    }
)

print("=" * 50)

response = agent.invoke(
    {
        "question": "What is my name?",
        "user_id": "demo-user",
        "channel_id": "local",
        "messages": [],
        "context": "",
        "history": "",
        "sources": [],
        "tool_results": [],
        "final_answer": "",
        "iteration": 0,
        "should_use_tools": False,
    }
)

print(response["final_answer"])