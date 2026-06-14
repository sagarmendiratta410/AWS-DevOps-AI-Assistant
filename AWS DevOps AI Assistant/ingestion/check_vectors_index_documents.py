from embeddings.bedrock_embeddings import BedrockEmbeddings
from vectorstore.opensearch_client import OpenSearchVectorStore
from vectorstore.index_manager import get_os_client
import os

client = get_os_client()

print(
    client.count(
        index=os.environ["OPENSEARCH_INDEX"]
    )
)
embedder = BedrockEmbeddings()
vs = OpenSearchVectorStore()

query = "incident management"

query_embedding = embedder.embed_query(query)

results = vs.similarity_search(
    query_embedding,
    k=3
)

for r in results:
    print("\nScore:", r["score"])
    print(r["text"][:200])