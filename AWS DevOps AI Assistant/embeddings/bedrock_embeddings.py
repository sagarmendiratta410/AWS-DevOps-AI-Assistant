import boto3
import json
import os
import time
import logging
import traceback

from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class BedrockEmbeddings:
    """
    Wrapper for Amazon Titan Embed Text v2.
    Supports both single queries and batch document embedding.
    """

    MODEL_ID = "amazon.titan-embed-text-v2:0"

    def __init__(self):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        reraise=True,
    )
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""

        body = json.dumps(
            {
                "inputText": text[:8192]
            }
        )

        response = self.client.invoke_model(
            modelId=self.MODEL_ID,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        result = json.loads(
            response["body"].read()
        )

        print("\n=== RAW RESPONSE KEYS ===")
        print(result.keys())

        if "embedding" not in result:
            raise ValueError(
                f"No 'embedding' field found. Response: {result}"
            )

        embedding = result["embedding"]

        print(f"\nEmbedding dimension returned: {len(embedding)}")

        return embedding

    def embed_documents(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Embed multiple documents.
        """

        embeddings = []

        for i, text in enumerate(texts):
            emb = self.embed_query(text)
            embeddings.append(emb)

            logger.info(
                f"Embedded document {i + 1}/{len(texts)}"
            )

            if (i + 1) % 20 == 0:
                time.sleep(0.5)

        return embeddings

    def __call__(self, text: str) -> List[float]:
        return self.embed_query(text)


# --------------------------------------------------
# TEST BLOCK
# --------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Testing Bedrock Embeddings...\n")

    try:
        embedder = BedrockEmbeddings()

        test_text = (
            "How do I restart a Kubernetes pod?"
        )

        embedding = embedder.embed_query(
            test_text
        )

        print("\nSUCCESS")
        print(f"Embedding length: {len(embedding)}")

        print("\nFirst 10 values:")
        print(embedding[:10])

    except Exception:
        print("\nFAILED\n")
        traceback.print_exc()