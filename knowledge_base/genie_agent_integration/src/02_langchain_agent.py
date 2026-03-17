# Databricks notebook source
# src/02_langchain_agent.py
#
# Pattern 2: LangChain Agent with Genie as a BaseTool
#
# WHY this pattern vs. the UC function:
#   - The LangChain agent can use MULTIPLE tools in one chain (Genie + other APIs)
#   - The agent can reason: "I need to check cost data first, then correlate with
#     a pipeline failure" — UC functions can't chain like this
#   - BaseTool gives you Python-level control: error handling, retries, formatting
#   - The CHAT_ZERO_SHOT_REACT agent decides autonomously whether to call Genie
#     or answer from its own knowledge
#
# Design decisions:
#   - DatabricksGenieTool starts a NEW conversation per invocation (stateless).
#     See pattern 5 for stateful per-user conversation management.
#   - The SDK auth chain (WorkspaceClient) is used instead of a hardcoded PAT.
#     This means the tool authenticates as whatever identity the notebook runs as.
#   - Poll-based status check is necessary: Genie is async — the API returns a
#     message_id and you must poll GET .../messages/{id} until status is terminal.

# COMMAND ----------

# %pip install -q databricks-sdk langchain langchain-community mlflow
# dbutils.library.restartPython()

# COMMAND ----------

import json
import time
from typing import Any, Dict, Optional

import mlflow
import requests
from databricks.sdk import WorkspaceClient
from langchain.agents import AgentType, initialize_agent
from langchain_community.chat_models import ChatDatabricks
from langchain_core.tools import BaseTool

mlflow.langchain.autolog()

# COMMAND ----------

# Parameters
dbutils.widgets.text("genie_space_id", "YOUR_SPACE_ID_HERE")
dbutils.widgets.text("llm_endpoint",   "databricks-meta-llama-3-3-70b-instruct")
dbutils.widgets.text("secret_scope",   "echostar-genie")
dbutils.widgets.text("secret_key",     "api_token")

GENIE_SPACE_ID = dbutils.widgets.get("genie_space_id")
LLM_ENDPOINT   = dbutils.widgets.get("llm_endpoint")
SECRET_SCOPE   = dbutils.widgets.get("secret_scope")
SECRET_KEY     = dbutils.widgets.get("secret_key")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Genie REST helper — encapsulates all HTTP calls to /api/2.0/genie
# ---------------------------------------------------------------------------

class _GenieClient:
    """
    Low-level Genie REST API client.

    Uses WorkspaceClient for auth so the caller does not need to manage PATs.
    Token is re-resolved on each call to handle short-lived OAuth tokens
    in App or job contexts.
    """

    def __init__(self, space_id: str) -> None:
        self._space_id = space_id
        self._w = WorkspaceClient()

    @property
    def _host(self) -> str:
        return self._w.config.host.rstrip("/")

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._w.config.token}",
            "Content-Type":  "application/json",
        }

    def _base(self) -> str:
        return f"{self._host}/api/2.0/genie/spaces/{self._space_id}"

    def start_conversation(self, question: str) -> Dict[str, Any]:
        """POST /start-conversation → {conversation_id, message_id}"""
        r = requests.post(
            f"{self._base()}/start-conversation",
            headers=self._headers,
            json={"content": question},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def follow_up(self, conversation_id: str, question: str) -> Dict[str, Any]:
        """POST /conversations/{id}/messages → {message_id}"""
        r = requests.post(
            f"{self._base()}/conversations/{conversation_id}/messages",
            headers=self._headers,
            json={"content": question},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def poll_message(
        self,
        conversation_id: str,
        message_id: str,
        timeout_s: int = 300,
    ) -> Dict[str, Any]:
        """Poll until message status is terminal (COMPLETED, EXECUTING_QUERY, FAILED)."""
        url     = f"{self._base()}/conversations/{conversation_id}/messages/{message_id}"
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            r = requests.get(url, headers=self._headers, timeout=30)
            r.raise_for_status()
            data   = r.json()
            status = data.get("status", "")
            if status in ("COMPLETED", "EXECUTING_QUERY", "FAILED", "CANCELED"):
                return data
            time.sleep(3)
        raise TimeoutError(f"Genie did not respond within {timeout_s}s")

    def get_query_result(self, conversation_id: str, message_id: str) -> Optional[Dict]:
        """GET /messages/{id}/query-result → statement_response payload"""
        r = requests.get(
            f"{self._base()}/conversations/{conversation_id}/messages/{message_id}/query-result",
            headers=self._headers,
            timeout=30,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


# COMMAND ----------

# ---------------------------------------------------------------------------
# LangChain BaseTool wrapper
# ---------------------------------------------------------------------------

class DatabricksGenieTool(BaseTool):
    """
    LangChain tool that wraps a Databricks Genie Space.

    Each invocation starts a FRESH conversation (stateless).
    The tool formats the response as a plain-English summary when available,
    or as a JSON table when Genie returns tabular data.

    For stateful per-user conversations, see 05_stateful_conversations.py.
    """

    name: str = "DatabricksGenie"
    description: str = (
        "Use this tool to answer questions about EchoStar platform costs, DBU usage, "
        "pipeline performance, and SQL warehouse spend. "
        "The tool queries live data via a Genie Space and returns either a "
        "text answer or tabular data. "
        "Input: a natural language question string. "
        "Do NOT use for questions that don't require data lookups."
    )

    space_id: str
    timeout_s: int = 300

    # Pydantic v1 pattern — exclude non-serializable client from model fields
    class Config:
        arbitrary_types_allowed = True

    def _get_client(self) -> _GenieClient:
        return _GenieClient(self.space_id)

    def _format_result(self, msg: Dict[str, Any], client: _GenieClient,
                       conversation_id: str, message_id: str) -> str:
        """Extract a human-readable answer from a completed Genie message."""
        status = msg.get("status", "")

        # Text-only answer (status = COMPLETED with text attachment)
        for att in msg.get("attachments", []):
            if "text" in att:
                return att["text"]["content"]

        # Tabular answer (status = EXECUTING_QUERY → fetch result)
        if status == "EXECUTING_QUERY":
            qr = client.get_query_result(conversation_id, message_id)
            if qr:
                try:
                    cols = [c["name"] for c in
                            qr["statement_response"]["manifest"]["schema"]["columns"]]
                    rows = qr["statement_response"]["result"].get("data_array", [])

                    # Pull SQL for transparency
                    sql = ""
                    for att in msg.get("attachments", []):
                        if "query" in att:
                            sql = att["query"].get("query", "")
                            break

                    return json.dumps({
                        "columns": cols,
                        "rows":    rows[:50],   # cap to avoid token overflow
                        "sql":     sql,
                    })
                except (KeyError, TypeError):
                    pass

        if status == "FAILED":
            return f"Genie query failed: {msg}"

        return f"Genie returned status={status} with no parseable answer."

    def _run(self, question: str) -> str:
        client = self._get_client()
        started = client.start_conversation(question)
        conv_id = started["conversation_id"]
        msg_id  = started["message_id"]
        msg     = client.poll_message(conv_id, msg_id, timeout_s=self.timeout_s)
        return self._format_result(msg, client, conv_id, msg_id)

    async def _arun(self, question: str) -> str:  # noqa: D102
        raise NotImplementedError("Async not supported — use _run")


# COMMAND ----------

# ---------------------------------------------------------------------------
# Build the agent
# ---------------------------------------------------------------------------

genie_tool = DatabricksGenieTool(space_id=GENIE_SPACE_ID)

chat_model = ChatDatabricks(
    endpoint=LLM_ENDPOINT,
    extra_params={"max_tokens": 1500, "temperature": 0.01},
)

agent = initialize_agent(
    tools=[genie_tool],
    llm=chat_model,
    agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5,
)

# COMMAND ----------

# ---------------------------------------------------------------------------
# Demo invocations
# ---------------------------------------------------------------------------

questions = [
    "What was the total DBU cost last month, broken down by SKU?",
    "Which team has the highest compute spend over the last 30 days?",
    "Were there any pipeline failures this week? What did they cost us?",
]

for q in questions:
    print(f"\n{'='*70}\nQ: {q}\n{'='*70}")
    result = agent.invoke(q)
    print(f"A: {result['output']}")
