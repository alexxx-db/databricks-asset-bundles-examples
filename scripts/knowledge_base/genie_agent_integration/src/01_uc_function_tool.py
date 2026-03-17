# Databricks notebook source
# src/01_uc_function_tool.py
#
# Pattern 1: Unity Catalog Python Function Wrapping a Genie Space
#
# WHY this pattern:
#   A UC Python function lets ANY SQL query or AI_QUERY() call invoke a Genie space
#   without importing Python libraries. This means:
#     - SQL analysts can call it from a notebook: SELECT my_catalog.genie_tools.ask_finops('...')
#     - AI_QUERY() can use it as a tool for LLM-powered SQL workflows
#     - It is subject to Unity Catalog RBAC — you grant EXECUTE to groups
#     - It persists across sessions; no need to reconstruct Python objects each run
#
# WHY the function is a CREATE OR REPLACE:
#   Idempotent — safe to run on every bundle deployment or from CI. If the Genie
#   space ID changes, just re-run this notebook with the new ID.
#
# Known limitation: UC Python functions run in a sandboxed environment that cannot
#   import external packages. The function uses only stdlib + requests (pre-installed).
#   The conversation_id in the function body is HARDCODED, meaning each invocation
#   continues the same conversation. For per-user isolation see pattern 5.

# COMMAND ----------

# Parameters injected by the DABs job task
dbutils.widgets.text("genie_space_id", "YOUR_SPACE_ID_HERE")
dbutils.widgets.text("uc_catalog",     "example_catalog")
dbutils.widgets.text("uc_schema",      "genie_tools")
dbutils.widgets.text("secret_scope",   "my-genie")
dbutils.widgets.text("secret_key",     "api_token")

genie_space_id = dbutils.widgets.get("genie_space_id")
uc_catalog     = dbutils.widgets.get("uc_catalog")
uc_schema      = dbutils.widgets.get("uc_schema")
secret_scope   = dbutils.widgets.get("secret_scope")
secret_key     = dbutils.widgets.get("secret_key")

print(f"Registering UC function in {uc_catalog}.{uc_schema}")
print(f"Genie space: {genie_space_id}")

# COMMAND ----------

# Ensure the schema exists before creating the function
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {uc_catalog}.{uc_schema}")

# COMMAND ----------

# MAGIC %sql
# MAGIC -- The conversation_id must exist in the target Genie space.
# MAGIC -- Start a conversation manually once, then paste the ID below,
# MAGIC -- OR use pattern 5 (stateful_conversations) for dynamic per-user IDs.
# MAGIC --
# MAGIC -- NOTE: The API token is read from secrets at function call time so it
# MAGIC --       is never embedded in the UC catalog.

# COMMAND ----------

# Build the CREATE OR REPLACE statement dynamically so we can interpolate
# the space_id and conversation_id from DABs parameters.
# The function body is a raw Python string embedded in SQL — this is the
# only way to pass a Genie space ID through a UC function without hardcoding.

create_fn_sql = f"""
CREATE OR REPLACE FUNCTION {uc_catalog}.{uc_schema}.ask_genie(question STRING)
RETURNS STRING
LANGUAGE PYTHON
COMMENT 'Ask a natural language question to the FinOps Genie space.
         Genie translates the question into SQL, executes it, and returns a
         plain-English answer plus the generated SQL.
         Use for: cost lookups, usage trends, pipeline analysis.
         Limitations: single-conversation context (no per-user isolation).
         For multi-user use cases, call the LangChain agent instead.'
AS $$
    import json
    import time
    import requests

    WORKSPACE_HOST   = spark.conf.get("spark.databricks.workspaceUrl")
    API_TOKEN        = dbutils.secrets.get("{secret_scope}", "{secret_key}")
    SPACE_ID         = "{genie_space_id}"
    BASE_URL         = f"https://{{WORKSPACE_HOST}}/api/2.0/genie/spaces/{{SPACE_ID}}"

    headers = {{
        "Authorization": f"Bearer {{API_TOKEN}}",
        "Content-Type":  "application/json",
    }}

    # Start a new conversation for each call (stateless, safe for SQL context)
    start_resp = requests.post(
        f"{{BASE_URL}}/start-conversation",
        headers=headers,
        json={{"content": question}},
        timeout=30,
    )
    start_resp.raise_for_status()
    data           = start_resp.json()
    conversation_id = data["conversation_id"]
    message_id      = data["message_id"]

    # Poll until Genie finishes generating the answer
    poll_url = f"{{BASE_URL}}/conversations/{{conversation_id}}/messages/{{message_id}}"
    for _ in range(60):   # 5-minute timeout
        poll_resp = requests.get(poll_url, headers=headers, timeout=30)
        poll_resp.raise_for_status()
        msg = poll_resp.json()
        status = msg.get("status", "")

        if status == "COMPLETED":
            # Text-only answer
            for att in msg.get("attachments", []):
                if "text" in att:
                    return att["text"]["content"]
            return "Genie returned no text answer."

        if status == "EXECUTING_QUERY":
            # Fetch the query result
            qr_url = f"{{poll_url}}/query-result"
            qr_resp = requests.get(qr_url, headers=headers, timeout=30)
            if qr_resp.ok:
                qr = qr_resp.json()
                try:
                    cols = [c["name"] for c in
                            qr["statement_response"]["manifest"]["schema"]["columns"]]
                    rows = qr["statement_response"]["result"].get("data_array", [])
                    # Return first 20 rows as JSON so caller can format
                    return json.dumps({{"columns": cols, "rows": rows[:20]}})
                except (KeyError, TypeError):
                    pass
            return "Genie executed a query but the result could not be parsed."

        if status in ("FAILED", "CANCELED"):
            return f"Genie query ended with status: {{status}}"

        time.sleep(5)

    return "Genie timed out after 5 minutes."
$$
"""

spark.sql(create_fn_sql)
print(f"Function created: {uc_catalog}.{uc_schema}.ask_genie")

# COMMAND ----------

# Smoke test — calls the function from SQL
result = spark.sql(f"""
  SELECT {uc_catalog}.{uc_schema}.ask_genie(
    'What were the top 5 most expensive pipeline runs last week?'
  ) AS answer
""")
result.show(truncate=False)

# COMMAND ----------

# Grant EXECUTE to the data consumers group so they can call it from SQL
# Adjust the group name for your environment.
spark.sql(f"GRANT EXECUTE ON FUNCTION {uc_catalog}.{uc_schema}.ask_genie TO `data-consumers`")
print("EXECUTE granted to data-consumers")
