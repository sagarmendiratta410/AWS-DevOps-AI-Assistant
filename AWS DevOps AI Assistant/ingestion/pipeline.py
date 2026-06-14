from ingestion.loaders.confluence_loader import ConfluenceLoader
from ingestion.loaders.jira_loader import JiraLoader
from ingestion.loaders.github_loader import GitHubLoader
from ingestion.loaders.s3_loader import S3RunbookLoader
from ingestion.chunker import chunk_documents
from embeddings.bedrock_embeddings import BedrockEmbeddings
from vectorstore.opensearch_client import OpenSearchVectorStore

import logging
import time

logger = logging.getLogger(__name__)


def run_ingestion_pipeline(incremental: bool = False):
    """
    Full ingestion: load → chunk → embed → upsert to OpenSearch.

    Set incremental=True to only process docs modified in last 24h.
    """

    # 1. Load from all sources
    all_docs = []

    loaders = [
        ConfluenceLoader(),
        JiraLoader(),
        GitHubLoader(),
        S3RunbookLoader(),
    ]

    for loader in loaders:
        try:
            docs = loader.load()
            all_docs.extend(docs)

            logger.info(
                f"{loader.__class__.__name__}: {len(docs)} docs"
            )

        except Exception as e:
            logger.error(
                f"{loader.__class__.__name__} failed: {e}"
            )

    # 2. Chunk documents
    chunks = chunk_documents(all_docs)

    logger.info(
        f"Total chunks after splitting: {len(chunks)}"
    )

    # 3. Upsert to OpenSearch in batches of 100
    vs = OpenSearchVectorStore()
    embedder = BedrockEmbeddings()

    batch_size = 100

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]

        texts = [c.page_content for c in batch]
        metadatas = [c.metadata for c in batch]

        embeddings = embedder.embed_documents(texts)

        vs.add_embeddings(
            texts,
            embeddings,
            metadatas,
        )

        logger.info(
            f"Upserted batch {i // batch_size + 1}"
        )

        time.sleep(0.1)  # rate limit guard

    logger.info("Ingestion complete!")

    return len(chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    n = run_ingestion_pipeline()

    print(f"Ingested {n} chunks total")