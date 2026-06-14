from ingestion.pipeline import chunk_documents
from ingestion.loaders.confluence_loader import ConfluenceLoader
from ingestion.loaders.jira_loader import JiraLoader
from ingestion.loaders.s3_loader import S3RunbookLoader
from ingestion.loaders.github_loader import GitHubLoader

all_docs = []

for loader in [
    ConfluenceLoader(),
    JiraLoader(),
    GitHubLoader(),
    S3RunbookLoader(),
]:
    all_docs.extend(loader.load())

chunks = chunk_documents(all_docs)

chunk_ids = [c.metadata["chunk_id"] for c in chunks]

print("Total chunks:", len(chunk_ids))
print("Unique chunk_ids:", len(set(chunk_ids)))