"""
genie_qa_reviewer / app.py
==========================
Databricks App that lets a Genie space owner view full, unredacted query
results for any conversation in the space — including conversations started
by other users.

WHY THIS WORKS
--------------
The Monitoring tab in the Genie UI redacts result payloads that belong to a
different user because Genie executes SQL under the *originating* user's
Unity Catalog identity. The native UI has no way to re-materialize those
results under a different identity.

A Databricks App runs as its own managed service principal. By granting that
SP CAN_MANAGE on the Genie space and SELECT on the backing UC tables, the
`/query-result` endpoint re-executes the stored SQL under the SP's identity,
returning full data — subject only to what the SP is authorized to see in UC.

PREREQUISITES (one-time, performed by a workspace admin)
--------------------------------------------------------
1. Deploy this bundle (which creates the app and its managed SP).
2. Grant the app's SP CAN_MANAGE on the Genie space:

   POST /api/2.0/permissions/genie/{SPACE_ID}
   {
     "access_control_list": [
       {"service_principal_name": "<app-sp-id>", "permission_level": "CAN_MANAGE"}
     ]
   }

   The app SP's application ID is visible in the App details page under
   "Databricks Apps" in the workspace UI.

3. Grant SELECT on the UC tables backing the space:

   GRANT USE CATALOG ON CATALOG <uc_catalog> TO `<app-sp-name>`;
   GRANT USE SCHEMA  ON SCHEMA  <uc_catalog>.<uc_schema> TO `<app-sp-name>`;
   GRANT SELECT      ON TABLE   <uc_catalog>.<uc_schema>.<table> TO `<app-sp-name>`;

   Repeat for every table the Genie space queries.

4. Grant CAN_USE on the SQL warehouse to the app SP (same pattern as above).

ENVIRONMENT VARIABLES (set in resources/genie_qa_reviewer.app.yml)
-------------------------------------------------------------------
GENIE_SPACE_ID  – 32-char hex ID of the target Genie space
WAREHOUSE_ID    – SQL warehouse used to re-run queries
UC_CATALOG      – Primary catalog backing the space (informational)
UC_SCHEMA       – Primary schema  backing the space (informational)
"""

from __future__ import annotations

import os
import time
from typing import Any

import pandas as pd
import requests
import streamlit as st
from databricks.sdk import WorkspaceClient

# ---------------------------------------------------------------------------
# Configuration from environment (injected by the App runtime from app.yml)
# ---------------------------------------------------------------------------

SPACE_ID      = os.environ.get("GENIE_SPACE_ID", "")
WAREHOUSE_ID  = os.environ.get("WAREHOUSE_ID", "")
UC_CATALOG    = os.environ.get("UC_CATALOG", "")
UC_SCHEMA     = os.environ.get("UC_SCHEMA", "")

# The App runtime provides DATABRICKS_HOST and a pre-authenticated token
# via the SDK's default credential chain — no explicit PAT needed.
WORKSPACE_HOST = os.environ.get("DATABRICKS_HOST", "").rstrip("/")


# ---------------------------------------------------------------------------
# Genie REST helpers
# ---------------------------------------------------------------------------

def _sdk_token() -> str:
    """
    Retrieve the short-lived OAuth token for the app's SP from the SDK.
    WorkspaceClient() automatically uses the App runtime's credential
    provider (equivalent to an M2M OAuth flow, but transparent).
    """
    w = WorkspaceClient()
    # The SDK exposes the resolved token via the config object.
    return w.config.token  # type: ignore[return-value]


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_sdk_token()}", "Content-Type": "application/json"}


def _genie_url(path: str) -> str:
    return f"{WORKSPACE_HOST}/api/2.0/genie/spaces/{SPACE_ID}/{path.lstrip('/')}"


# ── Conversation listing ────────────────────────────────────────────────────

def list_conversations_via_audit(limit: int = 100) -> list[dict[str, Any]]:
    """
    Query system.access.audit filtered to Genie API calls for this space.

    Returns a list of dicts with keys:
        conversation_id, message_id, user_email, question_text,
        event_time, rating

    Falls back to an empty list if the audit table is unavailable or the
    app SP lacks SELECT on system.access.audit.

    NOTE: audit log latency is typically 15–30 minutes.  For same-session
    monitoring use the manual lookup form below instead.
    """
    w = WorkspaceClient()
    try:
        result = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            wait_timeout="30s",
            statement="""
            SELECT
                get_json_object(request_params, '$.space_id')       AS space_id,
                get_json_object(request_params, '$.conversation_id') AS conversation_id,
                get_json_object(request_params, '$.message_id')      AS message_id,
                user_identity.email                                  AS user_email,
                event_time,
                -- question text is not in audit; placeholder for join
                NULL                                                 AS question_text,
                NULL                                                 AS rating
            FROM system.access.audit
            WHERE service_name  = 'genieService'
              AND action_name   = 'createConversationMessage'
              AND get_json_object(request_params, '$.space_id') = :space_id
              AND event_time    >= current_timestamp() - INTERVAL 30 DAYS
            ORDER BY event_time DESC
            LIMIT :lim
            """,
            parameters=[
                {"name": "space_id", "value": SPACE_ID,       "type": "STRING"},
                {"name": "lim",      "value": str(limit),     "type": "INT"},
            ],
        )
        schema  = [c.name for c in result.manifest.schema.columns]
        rows    = result.result.data_typed_array or []
        records = [dict(zip(schema, [v.str for v in r.values], strict=False)) for r in rows]
        return [r for r in records if r.get("conversation_id") and r.get("message_id")]
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Could not query audit log (SELECT on system.access.audit may not be granted): {exc}")
        return []


# ── Message detail ──────────────────────────────────────────────────────────

def get_message(conv_id: str, msg_id: str) -> dict[str, Any]:
    """Fetch the message payload (includes generated SQL + description)."""
    r = requests.get(_genie_url(f"conversations/{conv_id}/messages/{msg_id}"),
                     headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def extract_sql(message: dict[str, Any]) -> tuple[str, str]:
    """
    Pull the generated SQL and its description from a message payload.
    Returns (sql_text, description).  Either may be an empty string.
    """
    for attachment in message.get("attachments", []):
        if "query" in attachment:
            q = attachment["query"]
            return q.get("query", ""), q.get("description", "")
    return "", ""


# ── Query result ────────────────────────────────────────────────────────────

def _poll_query_result(conv_id: str, msg_id: str,
                       timeout_s: int = 60) -> dict[str, Any]:
    """
    Poll GET /query-result until the statement reaches a terminal state.
    Returns the final payload dict.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = requests.get(
            _genie_url(f"conversations/{conv_id}/messages/{msg_id}/query-result"),
            headers=_headers(), timeout=30,
        )
        if r.status_code == 404:
            raise RuntimeError("No query result found for this message.")
        r.raise_for_status()
        payload = r.json()
        state   = (payload.get("statement_response", {})
                          .get("status", {})
                          .get("state", "SUCCEEDED"))
        if state == "SUCCEEDED":
            return payload
        if state in ("FAILED", "CANCELED", "CLOSED"):
            err = (payload.get("statement_response", {})
                          .get("status", {})
                          .get("error", {})
                          .get("message", state))
            raise RuntimeError(f"Query execution ended with state {state}: {err}")
        time.sleep(2)
    raise TimeoutError(f"Query did not complete within {timeout_s}s")


def get_query_result(conv_id: str, msg_id: str) -> pd.DataFrame:
    """
    Retrieve the full query result for a message, re-executing if expired.

    1. Try GET /query-result  (returns cached result if still valid)
    2. If stale / missing, POST /execute-query to re-run, then poll
    3. Parse the result manifest + data into a DataFrame

    The SQL executes under the *App's SP identity*, so Unity Catalog grants
    on the SP determine what data is visible — not the original user's grants.
    This is what bypasses the per-user redaction in the native UI.
    """
    # Step 1: try cached result
    try:
        payload = _poll_query_result(conv_id, msg_id, timeout_s=5)
    except (RuntimeError, TimeoutError):
        payload = None

    # Step 2: re-execute if needed
    if payload is None:
        re = requests.post(
            _genie_url(f"conversations/{conv_id}/messages/{msg_id}/execute-query"),
            headers=_headers(), json={}, timeout=30,
        )
        re.raise_for_status()
        payload = _poll_query_result(conv_id, msg_id, timeout_s=60)

    # Step 3: parse into DataFrame
    sr      = payload.get("statement_response", {})
    columns = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
    rows    = sr.get("result", {}).get("data_typed_array", [])
    data    = [[v.get("str") for v in row.get("values", [])] for row in rows]
    return pd.DataFrame(data, columns=columns) if data else pd.DataFrame(columns=columns)


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Genie QA Reviewer",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Genie Space — Owner QA Reviewer")
st.caption(
    f"Space `{SPACE_ID or '⚠ GENIE_SPACE_ID not set'}` · "
    f"Warehouse `{WAREHOUSE_ID or '⚠ WAREHOUSE_ID not set'}` · "
    f"UC `{UC_CATALOG}.{UC_SCHEMA}`"
)

if not SPACE_ID:
    st.error(
        "**GENIE_SPACE_ID environment variable is not set.**  "
        "Set `--var space_id=<your-space-id>` when running "
        "`databricks bundle deploy` and redeploy."
    )
    st.stop()

# ── Source selector ─────────────────────────────────────────────────────────
st.subheader("Select a conversation to inspect")

source = st.radio(
    "How would you like to find the conversation?",
    options=["Audit log (last 30 days)", "Manual lookup"],
    horizontal=True,
)

conv_id: str = ""
msg_id:  str = ""

if source == "Audit log (last 30 days)":
    with st.spinner("Querying system.access.audit …"):
        records = list_conversations_via_audit(limit=200)

    if not records:
        st.info(
            "No records found.  The audit log has ~15 min latency and requires "
            "the app SP to have SELECT on `system.access.audit`.  "
            "Use **Manual lookup** to inspect a specific conversation immediately."
        )
    else:
        df_audit = pd.DataFrame(records)
        df_audit["event_time"] = pd.to_datetime(df_audit["event_time"], errors="coerce")
        df_audit = df_audit.sort_values("event_time", ascending=False)

        selected = st.dataframe(
            df_audit[["event_time", "user_email", "conversation_id", "message_id"]],
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True,
        )
        if selected["selection"]["rows"]:
            idx     = selected["selection"]["rows"][0]
            row     = df_audit.iloc[idx]
            conv_id = row["conversation_id"]
            msg_id  = row["message_id"]

else:  # Manual lookup
    st.markdown(
        "Copy the **conversation_id** and **message_id** from the Monitoring tab.  "
        "Click a row in the Monitoring feed, then read the IDs from the URL:  \n"
        "`/genie/rooms/<space_id>/conversations/<conversation_id>/messages/<message_id>`"
    )
    col1, col2 = st.columns(2)
    with col1:
        conv_id = st.text_input("conversation_id", placeholder="e.g. 01jt4abc…")
    with col2:
        msg_id  = st.text_input("message_id", placeholder="e.g. 01jt4def…")

# ── Detail panel ─────────────────────────────────────────────────────────────
if conv_id and msg_id:
    st.divider()

    with st.spinner("Fetching message …"):
        try:
            message = get_message(conv_id, msg_id)
        except Exception as exc:
            st.error(f"Could not fetch message: {exc}")
            st.stop()

    sql_text, description = extract_sql(message)

    col_sql, col_result = st.columns([1, 1], gap="large")

    with col_sql:
        st.subheader("Generated SQL")
        if sql_text:
            st.code(sql_text, language="sql")
            if description:
                st.caption(description)
        else:
            st.info("No SQL found in this message (may be a text-only response).")

    with col_result:
        st.subheader("Full Query Result")
        st.caption(
            "Re-executed under the app's service-principal identity.  "
            "Results reflect what the SP is authorized to see in Unity Catalog."
        )
        if sql_text:
            with st.spinner("Re-executing query …"):
                try:
                    df = get_query_result(conv_id, msg_id)
                    if df.empty:
                        st.info("Query returned zero rows.")
                    else:
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.caption(f"{len(df):,} rows · {len(df.columns)} columns")
                except Exception as exc:
                    st.error(
                        f"**Query execution failed.**  \n\n"
                        f"{exc}  \n\n"
                        "Check that the app SP has SELECT on the backing tables "
                        "and CAN_USE on the SQL warehouse."
                    )
        else:
            st.info("No executable SQL in this message.")
