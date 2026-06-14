# mcp/github_mcp.py

import os

from github import Github


class GitHubMCPClient:
    """
    MCP Client for GitHub.

    Supports:
    - Get Pull Request details
    - Get recent commits
    - Read repository information

    Works with:
    - Personal GitHub accounts
    - GitHub Organizations
    """

    def __init__(self):

        self.gh = Github(
            os.environ["GITHUB_TOKEN"]
        )

        # Owner can be either:
        # - Personal account (e.g. certifiedawsmaster)
        # - Organization (e.g. netflix)
        self.owner = os.environ[
            "GITHUB_ORG"
        ]

        print("\n" + "=" * 80)
        print("[GITHUB MCP] Initialized")
        print(f"Owner: {self.owner}")
        print("=" * 80)

    # =====================================================
    # GET PULL REQUEST DETAILS
    # =====================================================

    def get_pr(
        self,
        repo_name: str,
        pr_number: int,
    ) -> str:

        print("\n" + "=" * 80)
        print("[GITHUB MCP] GET PR")
        print(f"Repo : {repo_name}")
        print(f"PR   : {pr_number}")
        print("=" * 80)

        try:

            repo = self.gh.get_repo(
                f"{self.owner}/{repo_name}"
            )

            pr = repo.get_pull(
                pr_number
            )

            files_changed = [
                f.filename
                for f in pr.get_files()
            ]

            result = (
                f"PR #{pr.number}\n\n"
                f"Title: {pr.title}\n"
                f"Author: {pr.user.login}\n"
                f"State: {pr.state}\n"
                f"Merged: {pr.merged}\n"
                f"Changed Files: {pr.changed_files}\n\n"
                f"Files:\n"
                f"{chr(10).join(files_changed[:20])}\n\n"
                f"Description:\n"
                f"{pr.body or 'No description'}"
            )

            print(
                f"[GITHUB MCP] PR Loaded Successfully"
            )

            return result

        except Exception as e:

            print(
                f"[GITHUB MCP] ERROR: {e}"
            )

            return (
                f"GitHub PR lookup failed: {e}"
            )

    # =====================================================
    # GET RECENT COMMITS
    # =====================================================

    def get_recent_commits(
        self,
        repo_name: str,
        n: int = 10,
    ) -> str:

        print("\n" + "=" * 80)
        print("[GITHUB MCP] RECENT COMMITS")
        print(f"Owner : {self.owner}")
        print(f"Repo  : {repo_name}")
        print(f"Count : {n}")
        print("=" * 80)

        try:

            repo = self.gh.get_repo(
                f"{self.owner}/{repo_name}"
            )

            commits = list(
                repo.get_commits()[:n]
            )

            print(
                f"[GITHUB MCP] Found "
                f"{len(commits)} commits"
            )

            lines = []

            for commit in commits:

                lines.append(
                    f"{commit.sha[:7]} | "
                    f"{commit.commit.author.date} | "
                    f"{commit.commit.message.splitlines()[0]}"
                )

            return "\n".join(lines)

        except Exception as e:

            print(
                f"[GITHUB MCP] ERROR: {e}"
            )

            return (
                f"GitHub commit lookup failed: {e}"
            )