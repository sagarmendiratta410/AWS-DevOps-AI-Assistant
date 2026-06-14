from github import Github
import os
from dotenv import load_dotenv

load_dotenv()

# Authenticate
gh = Github(os.environ["GITHUB_TOKEN"])

# Get USER (not org)
user = gh.get_user()

print(f"Connected to GitHub user: {user.login}")

# Repo list from env
repos = os.environ["GITHUB_REPOS"].split(",")

for repo_name in repos:
    repo_name = repo_name.strip()

    try:
        repo = user.get_repo(repo_name)

        # Get all files recursively
        contents = repo.get_contents("")

        md_count = 0

        while contents:
            file = contents.pop(0)

            if file.type == "dir":
                contents.extend(repo.get_contents(file.path))
            elif file.name.endswith(".md"):
                md_count += 1

        print(f"✓ {repo_name}: {md_count} markdown files found")

    except Exception as e:
        print(f"✗ {repo_name}: {e}")