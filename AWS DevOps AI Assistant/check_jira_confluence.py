import os
import requests
from dotenv import load_dotenv
from jira import JIRA
from atlassian import Confluence

load_dotenv()

print("=" * 60)
print("DEVOPS AI ASSISTANT - CONNECTIVITY TEST")
print("=" * 60)

# ==================================================
# JIRA TEST
# ==================================================

try:
    print("\n[JIRA TEST]")

    jira = JIRA(
        server=os.environ["JIRA_URL"],
        basic_auth=(
            os.environ["CONFLUENCE_USERNAME"],
            os.environ["JIRA_API_TOKEN"]
        )
    )

    user = jira.myself()

    print(f"✅ Jira Authentication Successful")
    print(f"User: {user['displayName']}")

    project_key = os.environ["JIRA_PROJECT_KEY"]
    project = jira.project(project_key)

    print(f"✅ Jira Project Access Successful")
    print(f"Project Name: {project.name}")
    print(f"Project Key : {project.key}")

    # Use Jira Cloud REST API v3 directly
    search_url = f"{os.environ['JIRA_URL']}/rest/api/3/search/jql"

    payload = {
        "jql": f"project={project_key} ORDER BY updated DESC",
        "maxResults": 5,
        "fields": ["summary", "status"]
    }

    response = requests.post(
        search_url,
        auth=(
            os.environ["CONFLUENCE_USERNAME"],
            os.environ["JIRA_API_TOKEN"]
        ),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        json=payload
    )

    print(f"Search API Status: {response.status_code}")

    data = response.json()

    print("\nRecent Jira Issues:")

    if "issues" in data:
        for issue in data["issues"]:
            print(
                f"• {issue.get('key', 'N/A')} | "
                f"{issue.get('fields', {}).get('summary', 'No Summary')}"
            )

        print("✅ Jira Search API Working")

    else:
        print("⚠ No issues found")
        print(data)

except Exception as e:
    print(f"❌ Jira Test Failed")
    print(e)

# ==================================================
# CONFLUENCE TEST
# ==================================================

try:
    print("\n" + "=" * 60)
    print("[CONFLUENCE TEST]")
    print("=" * 60)

    confluence = Confluence(
        url=os.environ["CONFLUENCE_URL"],
        username=os.environ["CONFLUENCE_USERNAME"],
        password=os.environ["JIRA_API_TOKEN"],
        cloud=True
    )

    spaces = confluence.get_all_spaces(
        start=0,
        limit=20
    )

    print("✅ Confluence Authentication Successful")

    results = spaces.get("results", [])

    print(f"Found {len(results)} spaces")

    target_space = os.environ.get("CONFLUENCE_SPACE_KEY")

    if target_space:

        space = confluence.get_space(target_space)

        print(f"\n✅ Space Access Successful")
        print(f"Space Key : {space.get('key')}")
        print(f"Space Name: {space.get('name')}")

        pages = confluence.get_all_pages_from_space(
            target_space,
            start=0,
            limit=10
        )

        print(f"\nPages in {target_space}:")

        for page in pages:
            print(f"• {page['title']}")

    else:
        print("\nAvailable Spaces:")

        for space in results:
            print(
                f"• {space.get('key')} - "
                f"{space.get('name')}"
            )

except Exception as e:
    print("❌ Confluence Test Failed")
    print(e)

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)