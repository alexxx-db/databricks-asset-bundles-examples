# Databricks notebook source
# src/05_stateful_conversations.py
#
# Pattern 5: Multi-User Stateful Genie Conversations
#
# WHY stateful vs. new-conversation-per-call (patterns 2-4):
#   Genie maintains context within a conversation. If the user asks:
#     Turn 1: "What was DBU spend last month?"
#     Turn 2: "Break that down by team."
#     Turn 3: "Show only teams over $5K."
#   Genie understands "that" and "only teams" because it remembers prior turns.
#   Starting a new conversation each time loses this context.
#
# Per-user isolation:
#   In a multi-tenant setting (e.g. a Databricks App used by multiple people),
#   each user must have their OWN conversation_id. Sharing one conversation
#   means User A's context pollutes User B's queries.
#
#   This pattern maintains a Dict[user_id → conversation_id] in-process.
#   For persistence across restarts, store in Unity Catalog or Lakebase
#   (see genie_metadata_generator example for Lakebase pattern).
#
# new_conversation flag:
#   Users can explicitly reset context by saying "start fresh" or by calling
#   _run(..., new_conversation=True). The tool detects the phrase
#   "new_conversation: true" in the query string so it works from LangChain
#   agent input without needing a separate parameter.

# COMMAND ----------

# %pip install -q databricks-sdk langchain langchain-community
# dbutils.library.restartPython()

# COMMAND ----------

import json
import time
from typing import Any, Dict, Optional

import requests
from databricks.sdk import WorkspaceClient
from langchain_core.tools import BaseTool

# COMMAND ----------

dbutils.widgets.text("genie_space_id", "YOUR_SPACE_ID_HERE")
dbutils.widgets.text("secret_scope",   "my-genie")
dbutils.widgets.text("secret_key",     "api_token")

GENIE_SPACE_ID = dbutils.widgets.get("genie_space_id")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Stateful multi-user Genie tool
# ---------------------------------------------------------------------------

class StatefulDatabricksGenieTool(BaseTool):
    """
    LangChain tool with per-user Genie conversation state.

    Each user (identified by user_id) gets their own Genie conversation.
    Follow-up questions within the same user session continue the same
    conversation — Genie remembers prior context.

    State management:
      - In-process dict (this pattern): simple, lost on restart
      - Lakebase / UC table: persistent across restarts (see metadata generator)
      - Redis / external KV: for high-scale multi-pod deployments

    Usage in a LangChain agent:
      tool = StatefulDatabricksGenieTool(space_id=SPACE_ID)
      tool.run("What is DBU spend today?", user_id="alice@example.com")
      tool.run("Break that down by team.", user_id="alice@example.com")  # continues Alice's conversation
      tool.run("What is DBU spend today?", user_id="bob@example.com")    # fresh conversation for Bob
    """

    name: str = "StatefulDatabricksGenie"
    description: str = (
        "Use this to ask questions about platform data. "
        "Maintains conversation context per user so follow-up questions work. "
        "To start a new conversation, include 'new_conversation: true' in your query. "
        "Input: natural language question."
    )

    space_id: str
    timeout_s: int = 300

    # Mutable per-instance state — NOT in Pydantic model fields (use __init__ trick)
    _user_conversations: Dict[str, str] = {}    # user_id → conversation_id
    _default_user_id:   str = "default"

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, space_id: str, default_user_id: str = "default", **kwargs):
        super().__init__(space_id=space_id, **kwargs)
        object.__setattr__(self, "_user_conversations", {})
        object.__setattr__(self, "_default_user_id", default_user_id)

    # ── REST helpers ─────────────────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        w = WorkspaceClient()
        return {"Authorization": f"Bearer {w.config.token}", "Content-Type": "application/json"}

    def _base(self) -> str:
        w = WorkspaceClient()
        return f"{w.config.host.rstrip('/')}/api/2.0/genie/spaces/{self.space_id}"

    def _start_conversation(self, question: str) -> Dict[str, Any]:
        r = requests.post(
            f"{self._base()}/start-conversation",
            headers=self._headers(),
            json={"content": question},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def _follow_up(self, conversation_id: str, question: str) -> Dict[str, Any]:
        r = requests.post(
            f"{self._base()}/conversations/{conversation_id}/messages",
            headers=self._headers(),
            json={"content": question},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def _poll(self, conversation_id: str, message_id: str) -> Dict[str, Any]:
        url      = f"{self._base()}/conversations/{conversation_id}/messages/{message_id}"
        deadline = time.time() + self.timeout_s
        while time.time() < deadline:
            r = requests.get(url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            data   = r.json()
            status = data.get("status", "")
            if status in ("COMPLETED", "EXECUTING_QUERY", "FAILED", "CANCELED"):
                return data
            time.sleep(3)
        raise TimeoutError("Genie did not respond in time")

    def _get_query_result(self, conversation_id: str, message_id: str) -> Optional[Dict]:
        r = requests.get(
            f"{self._base()}/conversations/{conversation_id}/messages/{message_id}/query-result",
            headers=self._headers(),
            timeout=30,
        )
        return r.json() if r.ok else None

    def _extract_answer(self, msg: Dict, conversation_id: str, message_id: str) -> str:
        status = msg.get("status", "")

        for att in msg.get("attachments", []):
            if "text" in att:
                return att["text"]["content"]

        if status == "EXECUTING_QUERY":
            qr = self._get_query_result(conversation_id, message_id)
            if qr:
                try:
                    sr   = qr["statement_response"]
                    cols = [c["name"] for c in sr["manifest"]["schema"]["columns"]]
                    rows = sr["result"].get("data_array", [])
                    sql  = next(
                        (a["query"]["query"] for a in msg.get("attachments", []) if "query" in a),
                        ""
                    )
                    return json.dumps({"columns": cols, "rows": rows[:50], "sql": sql})
                except (KeyError, TypeError):
                    pass

        return f"Genie status={status}, no parseable answer."

    # ── Public interface ─────────────────────────────────────────────────────

    def reset_conversation(self, user_id: Optional[str] = None) -> None:
        """Force a new conversation on the next query for this user."""
        uid = user_id or self._default_user_id
        self._user_conversations.pop(uid, None)

    def get_conversation_id(self, user_id: Optional[str] = None) -> Optional[str]:
        """Return the current conversation_id for this user, or None."""
        uid = user_id or self._default_user_id
        return self._user_conversations.get(uid)

    def _run(
        self,
        query: str,
        user_id: Optional[str] = None,
        new_conversation: bool = False,
    ) -> str:
        uid = user_id or self._default_user_id

        # Allow the agent to signal a reset via the query string
        if "new_conversation: true" in query.lower():
            new_conversation = True
            query = query.lower().replace("new_conversation: true", "").strip()

        try:
            if new_conversation or uid not in self._user_conversations:
                # Start a fresh conversation
                resp            = self._start_conversation(query)
                conversation_id = resp["conversation_id"]
                message_id      = resp["message_id"]
                self._user_conversations[uid] = conversation_id
                print(f"[Genie] New conversation for {uid}: {conversation_id}")
            else:
                # Continue existing conversation
                conversation_id = self._user_conversations[uid]
                resp            = self._follow_up(conversation_id, query)
                message_id      = resp.get("message_id") or resp.get("id")
                print(f"[Genie] Follow-up in conversation {conversation_id}")

            msg = self._poll(conversation_id, message_id)
            return self._extract_answer(msg, conversation_id, message_id)

        except Exception as e:
            return f"Error: {e}"

    async def _arun(self, *args, **kwargs) -> str:
        raise NotImplementedError("Use _run")


# COMMAND ----------

# ---------------------------------------------------------------------------
# Demo: two "users" with separate conversation state
# ---------------------------------------------------------------------------

tool = StatefulDatabricksGenieTool(space_id=GENIE_SPACE_ID)

# Alice's conversation thread
alice_turns = [
    "What was total DBU spend last month?",
    "Break that down by SKU.",          # "that" refers to last month's spend
    "Which SKU had the highest growth vs the month before?",
]

# Bob's independent conversation thread
bob_turns = [
    "Show me pipeline run failures this week.",
    "What was the total cost of those failures?",   # "those" = this week's failures
]

print("=" * 70)
print("ALICE's conversation thread")
print("=" * 70)
for q in alice_turns:
    print(f"\nQ: {q}")
    answer = tool._run(q, user_id="alice@example.com")
    print(f"A: {answer[:500]}")   # truncate for readability

print("\n" + "=" * 70)
print("BOB's conversation thread (independent context)")
print("=" * 70)
for q in bob_turns:
    print(f"\nQ: {q}")
    answer = tool._run(q, user_id="bob@example.com")
    print(f"A: {answer[:500]}")

# COMMAND ----------

# Demonstrate reset
print("\n" + "=" * 70)
print("ALICE resets her conversation")
print("=" * 70)
answer = tool._run(
    "What was total DBU spend last month? new_conversation: true",
    user_id="alice@example.com",
)
print(f"Q: What was total DBU spend last month? (fresh)\nA: {answer[:500]}")

# Verify conversation IDs are per-user
print(f"\nAlice's conversation_id: {tool.get_conversation_id('alice@example.com')}")
print(f"Bob's   conversation_id: {tool.get_conversation_id('bob@example.com')}")
assert tool.get_conversation_id("alice@example.com") != tool.get_conversation_id("bob@example.com"), \
    "Users MUST have separate conversation IDs"
print("✓ Per-user isolation confirmed")
