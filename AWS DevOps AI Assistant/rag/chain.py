# chain.py

import os

from langchain_aws import ChatBedrock
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    RunnableLambda,
    RunnablePassthrough,
)

from rag.retriever import HybridRetriever


SYSTEM_PROMPT = """
You are an expert AWS DevOps assistant with deep knowledge of
this company's infrastructure, runbooks, and incident history.

You have been given relevant documentation excerpts below. Use them to answer
the engineer's question accurately and concisely.

Guidelines:
- Always cite the source document (title or URL) for key steps
- If the runbook has step numbers, reproduce them clearly
- If you are unsure, say so — do not hallucinate commands
- Format commands in code blocks
- If the question is about an error code, check the incident history first

Retrieved Documentation:
{context}
"""


def build_rag_chain():
    print("[RAG] Initializing HybridRetriever...")

    retriever = HybridRetriever(k=8)

    print(
        f"[RAG] Initializing Bedrock LLM: "
        f"{os.environ.get('BEDROCK_LLM_MODEL_ID')}"
    )

    llm = ChatBedrock(
        model_id=os.environ["BEDROCK_LLM_MODEL_ID"],
        region_name=os.environ["AWS_REGION"],
        model_kwargs={
            "max_tokens": 2048,
            "temperature": 0.1,
        },
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "{question}"),
        ]
    )

    def retrieve_and_format(inputs: dict) -> dict:
        question = inputs["question"]

        print("\n" + "=" * 80)
        print("[RAG] RETRIEVAL START")
        print("=" * 80)
        print(f"[RAG] Question:\n{question}")

        results = retriever.retrieve(question)

        print(f"[RAG] Retrieved {len(results)} chunks")

        if not results:
            print("[RAG] WARNING: No chunks returned from OpenSearch!")

        for idx, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})

            print("\n" + "-" * 60)
            print(f"Chunk #{idx}")
            print("-" * 60)
            print(f"Score: {result.get('score', 'N/A')}")
            print(f"URL: {metadata.get('url', 'N/A')}")
            print(f"Title: {metadata.get('title', 'N/A')}")
            print(f"Text Preview:\n{result.get('text', '')[:250]}")

        context = retriever.format_context(results)
        sources = [r["metadata"].get("url", "") for r in results]

        print("\n[RAG] Context Generated")
        print(f"[RAG] Context Length: {len(context)} characters")
        print(f"[RAG] Sources Found: {len(sources)}")
        print("=" * 80)
        print("[RAG] RETRIEVAL END")
        print("=" * 80)

        # FIX: return a clean dict with all keys explicitly set.
        # Previously this mutated `inputs` in place and the keys were not
        # guaranteed to survive through RunnablePassthrough.assign.
        return {
            "question": question,
            "context": context,
            "sources": sources,
        }

    # Chain structure:
    #   retrieve_and_format  →  { question, context, sources }
    #   RunnablePassthrough.assign(answer=...)
    #       adds 'answer' key while passing all existing keys through
    #   Final output: { question, context, sources, answer }
    chain = (
        RunnableLambda(retrieve_and_format)
        | RunnablePassthrough.assign(
            answer=(
                prompt
                | llm
                | StrOutputParser()
            )
        )
    )

    return chain


if __name__ == "__main__":
    print("\nStarting RAG Test...\n")

    chain = build_rag_chain()

    result = chain.invoke(
        {
            "question": "How do I roll back a Kubernetes deployment?"
        }
    )

    print("\n" + "=" * 80)
    print("FINAL ANSWER")
    print("=" * 80)
    print(result["answer"])

    print("\n" + "=" * 80)
    print("SOURCES")
    print("=" * 80)
    for source in result["sources"]:
        print(source)
