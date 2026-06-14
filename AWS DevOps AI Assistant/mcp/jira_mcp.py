import os
import requests


class JiraMCPClient:

    def __init__(self):

        self.base_url = os.environ["JIRA_URL"]

        self.auth = (
            os.environ["CONFLUENCE_USERNAME"],
            os.environ["JIRA_API_TOKEN"],
        )

        self.project = os.environ[
            "JIRA_PROJECT_KEY"
        ]

    def search_incidents(
        self,
        keyword: str,
        max_results: int = 5,
    ) -> str:

        jql = (
            f'project={self.project} '
            f'AND text ~ "{keyword}" '
            f'ORDER BY updated DESC'
        )

        url = (
            f"{self.base_url}"
            "/rest/api/3/search/jql"
        )

        response = requests.get(
            url,
            auth=self.auth,
            params={
                "jql": jql,
                "maxResults": max_results,
            },
        )

        response.raise_for_status()

        data = response.json()

        issues = data.get(
            "issues",
            []
        )

        if not issues:
            return (
                f"No Jira issues found "
                f"for '{keyword}'"
            )

        results = []

        for issue in issues:

            results.append(
                f"{issue['key']} | "
                f"{issue['fields']['summary']} | "
                f"{issue['fields']['status']['name']}"
            )

        return "\n".join(results)