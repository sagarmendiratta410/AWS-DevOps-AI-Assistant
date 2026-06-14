from typing import List
import hashlib
from ingestion.loaders.confluence_loader import ConfluenceLoader
from ingestion.loaders.jira_loader import JiraLoader
from ingestion.loaders.github_loader import GitHubLoader
from ingestion.loaders.s3_loader import S3RunbookLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Optimal chunk sizes for technical runbooks:
# chunk_size=800 — fits ~600 tokens, leaves room for query context
# chunk_overlap=150 — preserves step continuity across boundaries

SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=[
        "\n## ",
        "\n### ",
        "\n\n",
        "\n",
        " ",
        "",
    ],
    length_function=len,
)


def chunk_documents(docs: List[Document]) -> List[Document]:
    chunks = []

    for doc in docs:
        splits = SPLITTER.split_documents([doc])

        for i, chunk in enumerate(splits):
            # Stable deterministic ID for deduplication
            chunk_id = hashlib.md5(
                (
                    f"{doc.metadata.get('url', '')}"
                    f"-{i}"
                    f"-{chunk.page_content[:50]}"
                ).encode()
            ).hexdigest()

            chunk.metadata["chunk_id"] = chunk_id
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(splits)

            chunks.append(chunk)

    return chunks


# ---------------------------
# Test chunker directly
# ---------------------------
if __name__ == "__main__":
    from ingestion.loaders.confluence_loader import ConfluenceLoader

    print("Loading documents...")

    docs = ConfluenceLoader().load()

    print(f"Documents loaded: {len(docs)}")

    chunks = chunk_documents(docs)

    print(f"Chunks created: {len(chunks)}")

    if chunks:
        print("\nFirst Chunk Metadata:")
        print(chunks[0].metadata)

        print("\nFirst Chunk Content (first 300 chars):")
        print(chunks[0].page_content[:300])

        print("\nChunk Statistics:")
        for i, chunk in enumerate(chunks[:5]):
            print(
                f"Chunk {i}: "
                f"Length={len(chunk.page_content)}, "
                f"ChunkID={chunk.metadata['chunk_id']}"
            )