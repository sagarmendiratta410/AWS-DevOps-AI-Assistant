'''
This code creates a class called GitHubLoader whose job is to connect to GitHub and collect important documentation files (like README, runbooks, or docs) from multiple repositories, and convert them into structured Document objects. 
When the class starts (__init__), it connects to GitHub using a personal access token and reads the organization name and a list of repository names from environment variables. 
The main function load() then loops through each repository, tries to access it, and calls a helper function _load_repo() to fetch its files. Inside _load_repo(), the code starts from the root of the repository and explores folders and files one by one. If it finds specific folders like docs or .github, it goes inside them as well. For each file, it checks if it is a documentation-type file (like .md, .rst, or .txt). If yes, it reads the file content (which comes encoded in base64), decodes it into readable text, and then creates a Document object. 
This document stores the file content as page_content and keeps metadata such as repository name, file path, and GitHub URL. If any error happens while loading a repository or file, it logs a warning and continues, so the process doesn’t stop. Finally, after processing all repositories, it returns a list of all collected documents. In simple terms, this code automatically gathers useful documentation from GitHub repositories and prepares it in a structured format that can be used for search, analysis, or AI applications like chatbots.
'''


from github import Github
from langchain_core.documents import Document
from typing import List
import os
import logging
from dotenv import load_dotenv

# Load env
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubLoader:
    """Load README, docs, and markdown files from personal GitHub repos."""

    def __init__(self):
        try:
            self.token = os.environ.get("GITHUB_TOKEN")
            repos = os.environ.get("GITHUB_REPOS")

            if not self.token or not repos:
                raise ValueError("❌ Missing GITHUB_TOKEN or GITHUB_REPOS")

            self.repos = [r.strip() for r in repos.split(",")]
            self.gh = Github(self.token)

            # 🔥 IMPORTANT: Use user (not org)
            self.user = self.gh.get_user()

            logger.info(f"✅ Connected to GitHub user: {self.user.login}")

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            raise

    def load(self) -> List[Document]:
        docs = []

        try:
            for repo_name in self.repos:
                try:
                    logger.info(f"📦 Loading repo: {repo_name}")

                    repo = self.user.get_repo(repo_name)
                    repo_docs = self._load_repo(repo)

                    logger.info(f"✅ {repo_name}: {len(repo_docs)} files loaded")
                    docs.extend(repo_docs)

                except Exception as e:
                    logger.warning(f"⚠️ Failed loading {repo_name}: {e}")

            logger.info(f"🎉 Total GitHub documents: {len(docs)}")
            return docs

        except Exception as e:
            logger.error(f"❌ Load failed: {e}")
            return []

    def _load_repo(self, repo) -> List[Document]:
        docs = []

        try:
            contents = repo.get_contents("")

            while contents:
                file = contents.pop(0)

                # Traverse directories
                if file.type == "dir":
                    contents.extend(repo.get_contents(file.path))

                # Process documentation files
                elif file.type == "file" and self._is_doc_file(file.name):
                    try:
                        text = file.decoded_content.decode("utf-8", errors="ignore")

                        if len(text.strip()) < 20:
                            continue

                        docs.append(
                            Document(
                                page_content=text,
                                metadata={
                                    "source": "github",
                                    "repo": repo.full_name,
                                    "path": file.path,
                                    "url": file.html_url
                                }
                            )
                        )

                    except Exception as e:
                        logger.warning(f"⚠️ Error reading {file.path}: {e}")

        except Exception as e:
            logger.warning(f"⚠️ Repo error {repo.name}: {e}")

        return docs

    def _is_doc_file(self, name: str) -> bool:
        lower = name.lower()
        return any(lower.endswith(ext) for ext in (".md", ".rst", ".txt"))


# 🚀 MAIN EXECUTION
if __name__ == "__main__":
    try:
        loader = GitHubLoader()
        documents = loader.load()

        print(f"\n✅ Total GitHub documents loaded: {len(documents)}")

        # Preview first 3
        for i, doc in enumerate(documents[:3], start=1):
            print(f"\n--- Document {i} ---")
            print(f"Repo: {doc.metadata['repo']}")
            print(f"Path: {doc.metadata['path']}")
            print(f"URL: {doc.metadata['url']}")
            print(f"Content Preview:\n{doc.page_content[:300]}")

    except Exception as e:
        print(f"\n❌ Program failed: {e}")