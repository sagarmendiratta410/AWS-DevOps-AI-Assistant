'''
This code defines a class called ConfluenceLoader whose job is to connect to your Confluence account and pull out pages in a structured way. When the class starts (__init__), it creates a connection to Confluence using details like URL, username, API token, and space key—all taken from environment variables for security. 
The main function load() then begins fetching pages from that space in batches of 50 using a loop, so it can handle large numbers of pages efficiently. For each page, it extracts the HTML content and sends it to a helper function _html_to_text(), which uses BeautifulSoup to clean the HTML by removing unwanted elements (like macros) and converting it into plain readable text. If the cleaned text is too small (less than 50 characters), the page is skipped. Otherwise, the code creates a Document object containing the page’s text and metadata such as title, page ID, URL, space name, and last modified date. 
It keeps repeating this process until it either reaches the specified limit (default 500 pages) or no more pages are available. At the end, it logs how many pages were loaded and returns a list of these Document objects, which can be used later for search, AI models, or building a chatbot.
'''

from atlassian import Confluence
from langchain_core.documents import Document
from typing import List
import os
import logging
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfluenceLoader:
    """Load all pages from a Confluence space as LangChain Documents."""

    def __init__(self):
        try:
            self.url = os.environ.get('CONFLUENCE_URL')
            self.username = os.environ.get('CONFLUENCE_USERNAME')
            self.api_token = os.environ.get('CONFLUENCE_API_TOKEN')
            self.space_key = os.environ.get('CONFLUENCE_SPACE_KEY')

            if not all([self.url, self.username, self.api_token, self.space_key]):
                raise ValueError("❌ Missing one or more required environment variables")

            self.client = Confluence(
                url=self.url,
                username=self.username,
                password=self.api_token,
                cloud=True
            )

            logger.info("✅ Confluence client initialized successfully")

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            raise

    def load(self, limit: int = 500) -> List[Document]:
        docs = []
        start = 0

        try:
            while True:
                logger.info(f"📥 Fetching pages from {start}...")

                pages = self.client.get_all_pages_from_space(
                    self.space_key,
                    start=start,
                    limit=50,
                    expand='body.storage,version,ancestors'
                )

                if not pages:
                    logger.warning("⚠️ No more pages found")
                    break

                logger.info(f"✅ Fetched {len(pages)} pages")

                for page in pages:
                    try:
                        html = page['body']['storage']['value']
                        text = self._html_to_text(html)

                        # Skip very small/empty pages
                        if len(text.strip()) < 20:
                            continue

                        docs.append(
                            Document(
                                page_content=text,
                                metadata={
                                    'source': 'confluence',
                                    'page_id': page.get('id'),
                                    'title': page.get('title'),
                                    'url': f"{self.url}/wiki{page['_links']['webui']}",
                                    'space': self.space_key,
                                    'last_modified': page['version'].get('when')
                                }
                            )
                        )

                    except Exception as e:
                        logger.error(f"❌ Error processing page: {e}")

                start += 50

                if start >= limit:
                    logger.info("⛔ Reached limit")
                    break

            logger.info(f"🎉 Total documents loaded: {len(docs)}")
            return docs

        except Exception as e:
            logger.error(f"❌ Failed during load: {e}")
            return []

    def _html_to_text(self, html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')

        # Remove unwanted macros
        for tag in soup.find_all(['ac:structured-macro']):
            tag.decompose()

        return soup.get_text(separator=' ', strip=True)


# 🚀 MAIN EXECUTION
if __name__ == "__main__":
    try:
        loader = ConfluenceLoader()
        documents = loader.load(limit=100)

        print(f"\n✅ Total documents loaded: {len(documents)}")

        # Preview first 3 documents
        for i, doc in enumerate(documents[:3], start=1):
            print(f"\n--- Document {i} ---")
            print(f"Title: {doc.metadata['title']}")
            print(f"URL: {doc.metadata['url']}")
            print(f"Content Preview: {doc.page_content[:300]}")

    except Exception as e:
        print(f"\n❌ Program failed: {e}")