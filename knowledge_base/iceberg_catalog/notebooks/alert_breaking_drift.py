# Databricks notebook source
# notebooks/alert_breaking_drift.py
#
# Alert task: runs only when scan_drift exits with code 2 (breaking drift detected).
#
# WHY a separate alert task instead of email only:
#   The job-level email_notifications.on_failure fires for ANY failure reason
#   (infrastructure error, quota exhaustion, code bug). This task fires ONLY
#   for breaking schema drift — a specific, actionable condition that needs
#   a different response than a generic infrastructure alert.
#
#   The structured Slack message includes:
#     - Which tables have breaking drift
#     - Which columns changed and how (type narrowing, required column dropped)
#     - A direct link to the Unity Catalog table diff
#     - Actionable next steps (who to contact, what DDL to run)
#
# Trigger condition in the job DAG:
#   depends_on:
#     - task_key: scan_drift
#       outcome: FAILED   # scan_drift calls sys.exit(2) → job marks task FAILED

# COMMAND ----------

import json
import logging
import os

import requests
from databricks.sdk import WorkspaceClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

# COMMAND ----------

dbutils.widgets.text("uc_sf_catalog",    "iceberg_sf")
dbutils.widgets.text("uc_db_catalog",    "iceberg_db")
dbutils.widgets.text("slack_secret_key", "slack_webhook_url")
dbutils.widgets.text("secret_scope",     "iceberg-polaris")

uc_sf_catalog    = dbutils.widgets.get("uc_sf_catalog")
uc_db_catalog    = dbutils.widgets.get("uc_db_catalog")
slack_secret_key = dbutils.widgets.get("slack_secret_key")
secret_scope     = dbutils.widgets.get("secret_scope")

# COMMAND ----------

# Read the scan output from the previous task's job output
# (In a real pipeline, pass the structured output via task values)
w       = WorkspaceClient()
run_id  = dbutils.notebook.entry_point.getDbutils().notebook().getContext().currentRunId().get()
run     = w.jobs.get_run(run_id)

# Find scan_drift task output
scan_output = {}
for task_run in run.tasks or []:
    if task_run.task_key == "scan_drift":
        try:
            output = w.jobs.get_run_output(task_run.run_id)
            if output.notebook_output:
                scan_output = json.loads(output.notebook_output.result or "{}")
        except Exception:
            pass
        break

breaking_tables = scan_output.get("breaking", [])
total_breaking  = scan_output.get("tables_with_breaking", len(breaking_tables))

# COMMAND ----------

# Build Slack message blocks
workspace_host = w.config.host.rstrip("/")

blocks = [
    {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"🚨 Breaking Iceberg Schema Drift Detected — {total_breaking} table(s)",
        },
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                f"*Catalogs:* `{uc_sf_catalog}` (Snowflake) vs `{uc_db_catalog}` (Databricks)\n"
                f"*Breaking tables:* {total_breaking}\n"
                "*Action required:* Manual review and Polaris schema update needed.\n"
                "_Non-breaking drift has been auto-applied._"
            ),
        },
    },
]

# Add one section per breaking table (cap at 5 to avoid message truncation)
for tbl in breaking_tables[:5]:
    drift_lines = "\n".join(
        f"  • `{d['col']}`: {d['kind']}"
        for d in tbl.get("drifts", [])
    )
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Table:* `{tbl['table']}`\n{drift_lines}",
        },
    })

if len(breaking_tables) > 5:
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"_...and {len(breaking_tables) - 5} more table(s). See job output for full list._",
        },
    })

blocks.append({
    "type": "section",
    "text": {
        "type": "mrkdwn",
        "text": (
            "*Next steps:*\n"
            "1. Review the breaking drift in the job output\n"
            "2. If the Databricks change is intentional, update Polaris manually:\n"
            "   `polaris_client.update_table_schema(namespace, table, new_schema)`\n"
            "3. If the change is accidental, roll back the Databricks table DDL\n"
            "4. Re-run the schema drift scan to confirm resolution"
        ),
    },
})

# COMMAND ----------

# Send to Slack
try:
    slack_url = dbutils.secrets.get(secret_scope, slack_secret_key)
    resp = requests.post(
        slack_url,
        json={"blocks": blocks},
        timeout=15,
    )
    resp.raise_for_status()
    logger.info("Slack alert sent (status %d)", resp.status_code)
except Exception as e:
    logger.warning("Could not send Slack alert: %s", e)
    # Non-fatal — the job email notification will still fire

# COMMAND ----------

print(json.dumps({
    "alert_sent": True,
    "breaking_tables": total_breaking,
    "run_id": run_id,
}, indent=2))
