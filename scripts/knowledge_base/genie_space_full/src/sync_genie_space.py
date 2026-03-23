# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Sync Genie Space to Git
# MAGIC
# MAGIC This notebook reads the live serialized definition of a deployed Genie space
# MAGIC via the Genie Management API and commits it back to your git repository
# MAGIC (GitHub or GitLab). Run this after SMEs have refined the space in the UI.
# MAGIC
# MAGIC **Why this is needed:** Genie Spaces are not a native DAB resource type.
# MAGIC The space definition lives in the workspace after deployment, and SMEs can
# MAGIC edit it in the UI. Without a sync step, the repo drifts out of sync with
# MAGIC what is actually deployed, making future deploys destructive (they overwrite
# MAGIC SME work with the stale repo state).
# MAGIC
# MAGIC **Round-trip contract:** The deploy notebook writes `serialized_space` JSON
# MAGIC to disk and calls `create_space` / `update_space`. This notebook calls
# MAGIC `get_space(include_serialized_space=True)` and writes that same blob back to
# MAGIC the same file path. The blob is the canonical representation in both
# MAGIC directions -- no transformation is applied, which avoids the shared-ref
# MAGIC decomposition problem described in the README.
# MAGIC
# MAGIC ## Parameters
# MAGIC
# MAGIC | Parameter | Description |
# MAGIC |-----------|-------------|
# MAGIC | `space_name` | Filename stem under `genie_spaces/` (e.g. `sample_space` → `genie_spaces/sample_space.json`) |
# MAGIC | `space_title` | Space title as recorded in the state file (used to locate the stored space ID) |
# MAGIC | `git_provider` | `github` or `gitlab` |
# MAGIC | `git_repo` | Repository path: `owner/repo` (GitHub) or `group/project` (GitLab) |
# MAGIC | `git_branch` | Branch to commit to, or base branch when `create_review=true` (default: `main`) |
# MAGIC | `git_base_url` | GitLab only: your GitLab instance URL (default: `https://gitlab.com`) |
# MAGIC | `secret_scope` | Databricks secrets scope holding the git PAT |
# MAGIC | `secret_key` | Secret key within that scope |
# MAGIC | `create_review` | `true` → open a PR/MR for review; `false` → push directly to `git_branch` |

# COMMAND ----------

import base64
import json
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

import requests
from databricks.sdk import WorkspaceClient

# COMMAND ----------

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

space_name    = dbutils.widgets.get("space_name")     # e.g. "sample_space"
space_title   = dbutils.widgets.get("space_title")    # e.g. "NYC Taxi Trip Explorer"
git_provider  = dbutils.widgets.get("git_provider")   # "github" or "gitlab"
git_repo      = dbutils.widgets.get("git_repo")       # "owner/repo"
git_branch    = dbutils.widgets.get("git_branch")     # default: "main"
git_base_url  = dbutils.widgets.get("git_base_url")   # GitLab only, default: "https://gitlab.com"
secret_scope  = dbutils.widgets.get("secret_scope")
secret_key    = dbutils.widgets.get("secret_key")
create_review = dbutils.widgets.get("create_review").strip().lower() == "true"

if not git_branch:
    git_branch = "main"
if not git_base_url:
    git_base_url = "https://gitlab.com"

git_base_url = git_base_url.rstrip("/")

print(f"space_name:    {space_name}")
print(f"space_title:   {space_title}")
print(f"git_provider:  {git_provider}")
print(f"git_repo:      {git_repo}")
print(f"git_branch:    {git_branch}")
print(f"create_review: {create_review}")
print(f"git_base_url:  {git_base_url}  (used only for GitLab)")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Step 1: Resolve space_id from the state file written by deploy_genie_space.py
#
# The state file lives OUTSIDE the bundle sync directory so that `bundle deploy`
# does not delete it. It is keyed by the space title (spaces in the title
# replaced with underscores), matching the naming logic in deploy_genie_space.py.
# ---------------------------------------------------------------------------

w = WorkspaceClient()
username = w.current_user.me().user_name
state_dir  = f"/Workspace/Users/{username}/.genie_space_state"
state_file = os.path.join(state_dir, f"{space_title.replace(' ', '_')}.id")

print(f"\nLooking for state file: {state_file}")

try:
    with open(state_file) as f:
        space_id = f.read().strip()
    if not space_id:
        raise ValueError("State file is empty.")
    print(f"Resolved space_id: {space_id}")
except FileNotFoundError:
    raise RuntimeError(
        f"State file not found: {state_file}\n"
        "Has this space been deployed at least once by deploy_genie_space.py?\n"
        "If so, check that space_title matches the value used at deploy time."
    ) from None

# COMMAND ----------

# ---------------------------------------------------------------------------
# Step 2: Verify the space still exists and fetch its serialized definition
#
# include_serialized_space=True is required -- without it, get_space() returns
# only metadata (title, warehouse_id, description) and omits all instructions,
# example SQLs, sample questions, and table configs.
# ---------------------------------------------------------------------------

print(f"\nFetching Genie space {space_id} ...")
space = w.genie.get_space(space_id, include_serialized_space=True)

if not space.serialized_space:
    raise RuntimeError(
        "get_space() returned no serialized_space content. "
        "Verify that the space ID is correct and that the space has content."
    )

# Round-trip validate: confirm it parses as JSON before touching git.
try:
    json.loads(space.serialized_space)
except json.JSONDecodeError as e:
    raise RuntimeError(f"serialized_space is not valid JSON: {e}") from e

print(f"Fetched space: '{space.title}'  ({len(space.serialized_space)} bytes)")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Step 3: Determine the target file path in the repository
#
# Convention: genie_spaces/<space_name>.json, matching the layout assumed by
# deploy_genie_space.py when it resolves the config path at deploy time.
# ---------------------------------------------------------------------------

repo_file_path = f"genie_spaces/{space_name}.json"
commit_message = (
    f"chore: sync Genie space '{space.title}' from workspace\n\n"
    f"Space ID: {space_id}\n"
    f"Synced at: {datetime.now(timezone.utc).isoformat()}\n"
    f"Synced by: {username}"
)
print(f"\nTarget path in repo: {repo_file_path}")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Git provider abstraction
#
# Both providers expose the same four operations needed for this workflow:
#   get_file_sha  -- retrieve the current blob SHA (needed by GitHub for updates,
#                    and by GitLab to confirm the file exists before PUT vs POST)
#   push_file     -- create or update a file on a given branch
#   create_branch -- create a new branch from an existing one
#   create_review -- open a PR (GitHub) or MR (GitLab)
#
# Authentication uses a PAT read from Databricks Secrets. Never log the token.
# ---------------------------------------------------------------------------

git_token = dbutils.secrets.get(scope=secret_scope, key=secret_key)


class GitHubClient:
    """Minimal GitHub REST API client for file sync operations."""

    API_BASE = "https://api.github.com"

    def __init__(self, repo: str, token: str):
        self.repo = repo
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _url(self, path: str) -> str:
        return f"{self.API_BASE}/repos/{self.repo}{path}"

    def _check(self, resp: requests.Response, context: str) -> dict:
        if not resp.ok:
            raise RuntimeError(
                f"GitHub API error [{context}]: {resp.status_code} {resp.text[:400]}"
            )
        return resp.json()

    def get_file_sha(self, path: str, branch: str) -> Optional[str]:
        """Return the current blob SHA for a file, or None if it does not exist."""
        resp = requests.get(
            self._url(f"/contents/{path}"),
            params={"ref": branch},
            headers=self.headers,
            timeout=30,
        )
        if resp.status_code == 404:
            return None
        self._check(resp, f"get_file_sha({path})")
        return resp.json()["sha"]

    def push_file(self, path: str, content: str, branch: str, message: str) -> str:
        """Create or update a file. Returns the commit SHA."""
        existing_sha = self.get_file_sha(path, branch)
        body = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if existing_sha:
            body["sha"] = existing_sha
        resp = requests.put(self._url(f"/contents/{path}"), headers=self.headers, json=body, timeout=30)
        data = self._check(resp, f"push_file({path})")
        return data["commit"]["sha"]

    def create_branch(self, new_branch: str, from_branch: str) -> None:
        """Create new_branch pointing at the HEAD of from_branch."""
        # Resolve from_branch HEAD SHA.
        resp = requests.get(self._url(f"/git/ref/heads/{from_branch}"), headers=self.headers, timeout=30)
        base_sha = self._check(resp, f"resolve_branch({from_branch})")["object"]["sha"]
        resp = requests.post(
            self._url("/git/refs"),
            headers=self.headers,
            json={"ref": f"refs/heads/{new_branch}", "sha": base_sha},
            timeout=30,
        )
        self._check(resp, f"create_branch({new_branch})")

    def open_pr(self, head: str, base: str, title: str, body: str) -> str:
        """Open a pull request. Returns the PR HTML URL."""
        resp = requests.post(
            self._url("/pulls"),
            headers=self.headers,
            json={"title": title, "body": body, "head": head, "base": base},
            timeout=30,
        )
        data = self._check(resp, "open_pr")
        return data["html_url"]


class GitLabClient:
    """Minimal GitLab REST API client for file sync operations."""

    def __init__(self, repo: str, token: str, base_url: str = "https://gitlab.com"):
        self.base_url = base_url.rstrip("/")
        self.token = token
        # URL-encode the full project path for use in API endpoints.
        self.project_id = urllib.parse.quote(repo, safe="")
        self.headers = {"PRIVATE-TOKEN": token}

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v4/projects/{self.project_id}{path}"

    def _check(self, resp: requests.Response, context: str) -> dict:
        if not resp.ok:
            raise RuntimeError(
                f"GitLab API error [{context}]: {resp.status_code} {resp.text[:400]}"
            )
        return resp.json()

    def get_file_sha(self, path: str, branch: str) -> Optional[str]:
        """Return the blob_id (SHA) for a file, or None if not found."""
        resp = requests.get(
            self._url(f"/repository/files/{urllib.parse.quote(path, safe='')}"),
            params={"ref": branch},
            headers=self.headers,
            timeout=30,
        )
        if resp.status_code == 404:
            return None
        self._check(resp, f"get_file_sha({path})")
        return resp.json().get("blob_id")

    def push_file(self, path: str, content: str, branch: str, message: str) -> str:
        """Create or update a file. Returns the commit SHA."""
        encoded_path = urllib.parse.quote(path, safe="")
        existing_sha = self.get_file_sha(path, branch)
        method = requests.put if existing_sha else requests.post
        resp = method(
            self._url(f"/repository/files/{encoded_path}"),
            headers=self.headers,
            json={
                "branch": branch,
                "content": content,
                "commit_message": message,
                "encoding": "text",
            },
            timeout=30,
        )
        data = self._check(resp, f"push_file({path})")
        return data.get("id", "")  # GitLab returns the file path, not commit SHA here

    def create_branch(self, new_branch: str, from_branch: str) -> None:
        """Create new_branch from from_branch."""
        resp = requests.post(
            self._url("/repository/branches"),
            headers=self.headers,
            json={"branch": new_branch, "ref": from_branch},
            timeout=30,
        )
        self._check(resp, f"create_branch({new_branch})")

    def open_mr(self, source: str, target: str, title: str, description: str) -> str:
        """Open a merge request. Returns the MR web URL."""
        resp = requests.post(
            self._url("/merge_requests"),
            headers=self.headers,
            json={
                "source_branch": source,
                "target_branch": target,
                "title": title,
                "description": description,
                "remove_source_branch": True,
            },
            timeout=30,
        )
        data = self._check(resp, "open_mr")
        return data["web_url"]


def make_git_client(provider: str, repo: str, token: str, base_url: str):
    if provider == "github":
        return GitHubClient(repo, token)
    elif provider == "gitlab":
        return GitLabClient(repo, token, base_url)
    else:
        raise ValueError(f"Unsupported git_provider: {provider!r}. Use 'github' or 'gitlab'.")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Step 4: Resolve the target branch
#
# If create_review=True, we push to a short-lived sync branch and then open a
# PR/MR targeting git_branch (e.g. main). This lets engineers review what the
# SME changed before it merges.
#
# Branch name is deterministic per space so repeated sync runs don't pile up
# open PRs -- they push to the same branch, updating the existing PR/MR.
# ---------------------------------------------------------------------------

git_client = make_git_client(git_provider, git_repo, git_token, git_base_url)

if create_review:
    # Deterministic branch name: sync/<space_name> -- one open PR/MR per space
    sync_branch = f"sync/{space_name}"
    print(f"\nCreating/updating sync branch: {sync_branch} (base: {git_branch})")

    # Create the branch only if it does not already exist.
    try:
        git_client.create_branch(sync_branch, git_branch)
        print(f"  Created new branch: {sync_branch}")
    except RuntimeError as e:
        if "already exists" in str(e) or "400" in str(e):
            print(f"  Branch {sync_branch} already exists -- will push to it.")
        else:
            raise

    push_target = sync_branch
else:
    push_target = git_branch
    print(f"\nPushing directly to branch: {push_target}")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Step 5: Commit the serialized_space JSON to the repository
#
# Pretty-print the JSON before writing so that git diffs are readable.
# The round-trip through json.loads / json.dumps is safe because we already
# validated the content in Step 2.
# ---------------------------------------------------------------------------

pretty_content = json.dumps(json.loads(space.serialized_space), indent=2, ensure_ascii=False)

print(f"\nWriting {len(pretty_content)} bytes to {repo_file_path} on branch {push_target} ...")
commit_result = git_client.push_file(
    path=repo_file_path,
    content=pretty_content,
    branch=push_target,
    message=commit_message,
)
print(f"Committed: {commit_result}")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Step 6: Open a PR (GitHub) or MR (GitLab) if requested
# ---------------------------------------------------------------------------

review_url = None

if create_review:
    review_title = f"sync: Genie space '{space.title}' from workspace"
    review_body = (
        f"Automated sync of Genie space **{space.title}** back to git.\n\n"
        f"- Space ID: `{space_id}`\n"
        f"- Synced at: {datetime.now(timezone.utc).isoformat()}\n"
        f"- Synced by: {username}\n"
        f"- File: `{repo_file_path}`\n\n"
        "Review the diff to verify SME edits before merging. "
        "Once merged, run the deploy job to promote these changes to other targets."
    )

    if git_provider == "github":
        review_url = git_client.open_pr(
            head=push_target,
            base=git_branch,
            title=review_title,
            body=review_body,
        )
        print(f"\nPull Request opened: {review_url}")
    else:
        review_url = git_client.open_mr(
            source=push_target,
            target=git_branch,
            title=review_title,
            description=review_body,
        )
        print(f"\nMerge Request opened: {review_url}")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

workspace_host = w.config.host.rstrip("/")
space_url = f"{workspace_host}/genie/rooms/{space_id}"

print("\n" + "=" * 60)
print("Sync complete.")
print(f"  Space:       {space.title}  ({space_id})")
print(f"  Space URL:   {space_url}")
print(f"  Repo file:   {repo_file_path}")
print(f"  Branch:      {push_target}")
if review_url:
    print(f"  Review URL:  {review_url}")
print("=" * 60)
print()
print("Next steps:")
if create_review:
    print(f"  1. Review and merge the PR/MR at: {review_url}")
    print("  2. After merge, run the deploy job to push changes to other targets.")
else:
    print("  1. Run the deploy job to push this config to other targets if needed.")
