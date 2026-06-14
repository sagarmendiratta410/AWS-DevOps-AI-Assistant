import boto3
import os
import io
import logging
from typing import List
from langchain_core.documents import Document
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class S3RunbookLoader:
    """Load PDF and text runbooks from S3 as LangChain Documents."""

    def __init__(self):
        try:
            self.region = os.environ.get("AWS_REGION")
            self.bucket = os.environ.get("RUNBOOK_S3_BUCKET")

            if not self.region or not self.bucket:
                raise ValueError("❌ Missing AWS_REGION or RUNBOOK_S3_BUCKET")

            self.s3 = boto3.client("s3", region_name=self.region)

            logger.info("✅ S3 client initialized successfully")

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            raise

    def load(self, limit: int = 100) -> List[Document]:
        docs = []
        count = 0

        try:
            paginator = self.s3.get_paginator("list_objects_v2")

            for page in paginator.paginate(Bucket=self.bucket):
                contents = page.get("Contents", [])

                if not contents:
                    logger.warning("⚠️ No files found in bucket")
                    break

                for obj in contents:
                    key = obj["Key"]

                    # 🚫 Skip folders
                    if key.endswith("/"):
                        continue

                    logger.info(f"📥 Processing: {key}")

                    try:
                        if key.endswith(".pdf"):
                            pdf_docs = self._load_pdf(key)
                            docs.extend(pdf_docs)
                            count += len(pdf_docs)

                        elif key.endswith((".md", ".txt")):
                            doc = self._load_text(key)
                            docs.append(doc)
                            count += 1

                    except Exception as e:
                        logger.warning(f"❌ Failed: {key} | {e}")

                    if count >= limit:
                        logger.info("⛔ Reached limit")
                        return docs

            logger.info(f"🎉 Total S3 documents loaded: {len(docs)}")
            return docs

        except Exception as e:
            logger.error(f"❌ Load failed: {e}")
            return []

    def _load_pdf(self, key: str) -> List[Document]:
        body = self.s3.get_object(
            Bucket=self.bucket,
            Key=key
        )["Body"].read()

        reader = PdfReader(io.BytesIO(body))

        documents = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()

            if text and text.strip():
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": "s3",
                            "bucket": self.bucket,
                            "key": key,
                            "page": i,
                            "title": key.split("/")[-1],
                            "url": f"s3://{self.bucket}/{key}",
                        },
                    )
                )

        return documents

    def _load_text(self, key: str) -> Document:
        body = self.s3.get_object(
            Bucket=self.bucket,
            Key=key
        )["Body"].read().decode("utf-8", errors="ignore")

        return Document(
            page_content=body,
            metadata={
                "source": "s3",
                "bucket": self.bucket,
                "key": key,
                "title": key.split("/")[-1],
                "url": f"s3://{self.bucket}/{key}",
            },
        )


# 🚀 MAIN TEST (VERY IMPORTANT)
if __name__ == "__main__":
    try:
        loader = S3RunbookLoader()
        documents = loader.load(limit=20)

        print(f"\n✅ Total documents loaded: {len(documents)}")

        # Preview first 3 docs
        for i, doc in enumerate(documents[:3], 1):
            print(f"\n--- Document {i} ---")
            print(f"Title: {doc.metadata.get('title')}")
            print(f"Source: {doc.metadata.get('source')}")
            print(f"URL: {doc.metadata.get('url')}")
            print(f"Preview: {doc.page_content[:200]}")

    except Exception as e:
        print(f"\n❌ Program failed: {e}")