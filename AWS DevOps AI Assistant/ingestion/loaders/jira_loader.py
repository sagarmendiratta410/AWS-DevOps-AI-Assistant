import os
import requests
import logging
from typing import List
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from langchain_core.documents import Document

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JiraLoader:
    """Jira Loader using NEW API: /rest/api/3/search/jql"""

    def __init__(self):
        try:
            self.url = os.environ.get("JIRA_URL")
            self.username = os.environ.get("CONFLUENCE_USERNAME")
            self.api_token = os.environ.get("JIRA_API_TOKEN")
            self.project = os.environ.get("JIRA_PROJECT_KEY")

            if not all([self.url, self.username, self.api_token, self.project]):
                raise ValueError("❌ Missing env variables")

            self.auth = HTTPBasicAuth(self.username, self.api_token)

            self.headers = {
                "Accept": "application/json"
            }

            logger.info("✅ Jira client initialized")

        except Exception as e:
            logger.error(f"❌ Init failed: {e}")
            raise

    def load(self, limit: int = 100) -> List[Document]:
        docs = []
        start_at = 0

        search_url = f"{self.url}/rest/api/3/search/jql"

        try:
            while True:
                logger.info(f"📥 Fetching issues from {start_at}...")

                response = requests.get(
                    search_url,
                    auth=self.auth,
                    headers=self.headers,
                    params={
                        "jql": f"project={self.project} ORDER BY updated DESC",
                        "startAt": start_at,
                        "maxResults": 50,
                        "fields": "summary,status,priority,description"
                    }
                )

                if response.status_code != 200:
                    logger.error(f"❌ API Error: {response.text}")
                    break

                data = response.json()
                issues = data.get("issues", [])

                if not issues:
                    logger.warning("⚠️ No more issues")
                    break

                logger.info(f"✅ Fetched {len(issues)} issues")

                for issue in issues:
                    fields = issue.get("fields", {})

                    summary = fields.get("summary", "No Summary")
                    status = fields.get("status", {}).get("name", "No Status")
                    priority = fields.get("priority", {}) or {}
                    priority_name = priority.get("name", "None")

                    description = self._extract_text(fields.get("description"))

                    text = f"""
Issue: {issue.get('key')}
Summary: {summary}
Status: {status}
Priority: {priority_name}

Description:
{description}
"""

                    docs.append(
                        Document(
                            page_content=text.strip(),
                            metadata={
                                "issue_key": issue.get("key"),
                                "title": summary,
                                "status": status,
                                "priority": priority_name,
                                "url": f"{self.url}/browse/{issue.get('key')}"
                            }
                        )
                    )

                start_at += 50

                if start_at >= limit:
                    logger.info("⛔ Reached limit")
                    break

            logger.info(f"🎉 Total docs loaded: {len(docs)}")
            return docs

        except Exception as e:
            logger.error(f"❌ Load failed: {e}")
            return []

    # ✅ Safe text extractor
    def _extract_text(self, content):
        if not content:
            return ""

        result = []

        def walk(node):
            if isinstance(node, dict):
                if "text" in node:
                    result.append(node["text"])
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(content)
        return " ".join(result)


# 🚀 RUN
if __name__ == "__main__":
    loader = JiraLoader()
    docs = loader.load(limit=100)

    print(f"\n✅ Total documents loaded: {len(docs)}")

    for i, doc in enumerate(docs[:3], 1):
        print(f"\n--- Issue {i} ---")
        print(f"Key: {doc.metadata['issue_key']}")
        print(f"Title: {doc.metadata['title']}")
        print(f"URL: {doc.metadata['url']}")
        print(f"Preview:\n{doc.page_content[:300]}")