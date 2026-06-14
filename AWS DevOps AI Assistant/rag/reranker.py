# rag/reranker.py

import json
import os

from langchain_aws import ChatBedrock


class BedrockReranker:

    def __init__(self):

        self.llm = ChatBedrock(
            model_id=os.environ["BEDROCK_LLM_MODEL_ID"],
            region_name=os.environ["AWS_REGION"],
            model_kwargs={
                "temperature": 0
            }
        )

    def rerank(
        self,
        question: str,
        documents: list
    ):

        docs = []

        for idx, result in enumerate(documents):

            docs.append(
                f"""
Document {idx}

Title:
{result["metadata"].get("title","")}

Content:
{result["text"][:500]}
"""
            )

        prompt = f"""
You are a retrieval reranker.

Question:
{question}

Rank the documents by relevance.

Return ONLY valid JSON.

Example:

[
  {{
    "document_id": 3,
    "score": 0.95
  }},
  {{
    "document_id": 1,
    "score": 0.80
  }}
]

Documents:

{chr(10).join(docs)}
"""

        try:

            response = self.llm.invoke(prompt)

            rankings = json.loads(
                response.content
            )

            reranked = []

            for item in rankings:

                doc_id = item["document_id"]

                if doc_id >= len(documents):
                    continue

                result = documents[doc_id]

                result["rerank_score"] = (
                    item["score"]
                )

                reranked.append(result)

            return reranked

        except Exception as e:

            print(
                f"[RERANK] ERROR: {e}"
            )

            return documents