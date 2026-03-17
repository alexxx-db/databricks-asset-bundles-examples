# Databricks notebook source
# src/03_genie_rag_chain.py
#
# Pattern 3: Genie as a Retriever in a LangChain RAG Chain (MLflow Logged)
#
# WHY this pattern vs. the agent in pattern 2:
#   - The agent in pattern 2 reasons about WHEN to call Genie.
#   - This RAG chain ALWAYS routes through Genie as the retriever, then passes
#     the result to an LLM for synthesis/interpretation.
#   - Tighter latency profile: one Genie call → one LLM call (no agent loop).
#   - MLflow logging makes the chain deployable to Model Serving for production.
#   - Chat history aware: a query rewrite step handles "what about last week?"
#     follow-ups by translating them into self-contained questions before
#     sending to Genie.
#
# Chain architecture:
#   user messages
#       │
#       ├─ extract_user_query ─────────────────────────────────────────────┐
#       ├─ extract_chat_history                                            │
#       │                                                                  │
#       │  (if history exists) ─ rewrite_query_prompt → LLM → rewritten   │
#       │  (no history)        ─ pass through original query ──────────────┤
#       │                                                                  ▼
#       │                                                     call_genie (retriever)
#       │                                                            │
#       │                                                   format_genie_context
#       │                                                            │
#       └── synthesis_prompt (context + history + question) → LLM → answer

# COMMAND ----------

# %pip install -q databricks-sdk langchain langchain-community mlflow
# dbutils.library.restartPython()

# COMMAND ----------

import json
import os
import time
from operator import itemgetter
from typing import Any, Dict, List, Optional

import mlflow
import requests
import yaml
from databricks.sdk import WorkspaceClient
from langchain.tools import tool
from langchain_community.chat_models import ChatDatabricks
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough

mlflow.langchain.autolog()

# COMMAND ----------

dbutils.widgets.text("genie_space_id", "YOUR_SPACE_ID_HERE")
dbutils.widgets.text("llm_endpoint",   "databricks-meta-llama-3-3-70b-instruct")
dbutils.widgets.text("secret_scope",   "my-genie")
dbutils.widgets.text("secret_key",     "api_token")

GENIE_SPACE_ID = dbutils.widgets.get("genie_space_id")
LLM_ENDPOINT   = dbutils.widgets.get("llm_endpoint")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Chain configuration (saved as YAML for MLflow ModelConfig)
# ---------------------------------------------------------------------------

chain_config = {
    "databricks_resources": {
        "llm_endpoint_name": LLM_ENDPOINT,
        "genie_space_id":    GENIE_SPACE_ID,
    },
    "llm_config": {
        "llm_parameters": {"max_tokens": 1500, "temperature": 0.01},
        "synthesis_prompt": (
            "You are a trusted data analyst assistant. "
            "Use only the information provided to answer the question. "
            "If the data is tabular, summarize key insights. "
            "Always cite specific numbers from the data. "
            "Here is the data: {context}"
        ),
        "rewrite_prompt": (
            "Given the chat history below, rewrite the user's follow-up question "
            "into a fully self-contained query that could be sent directly to a "
            "data API with no prior context. "
            "Return ONLY the rewritten query, nothing else.\n\n"
            "Chat history: {chat_history}\n\n"
            "Question: {question}"
        ),
    },
    "input_example": {
        "messages": [
            {"role": "user", "content": "What was our total DBU spend last month?"}
        ]
    },
}

with open("genie_rag_config.yaml", "w") as f:
    yaml.dump(chain_config, f)

# COMMAND ----------

# ---------------------------------------------------------------------------
# Write chain.py for MLflow logging
# This module is the artifact that gets logged and served by Model Serving.
# ---------------------------------------------------------------------------

chain_py = '''
import json
import os
import time
from operator import itemgetter
from typing import Any, Dict

import mlflow
import requests
from databricks.sdk import WorkspaceClient
from langchain.tools import tool
from langchain_community.chat_models import ChatDatabricks
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough

mlflow.langchain.autolog()

model_config       = mlflow.models.ModelConfig(development_config="genie_rag_config.yaml")
resources          = model_config.get("databricks_resources")
llm_cfg            = model_config.get("llm_config")
GENIE_SPACE_ID     = resources["genie_space_id"]
LLM_ENDPOINT       = resources["llm_endpoint_name"]


# ── Genie retriever tool ─────────────────────────────────────────────────────

def _genie_headers() -> Dict[str, str]:
    w = WorkspaceClient()
    return {"Authorization": f"Bearer {w.config.token}", "Content-Type": "application/json"}


def _genie_base() -> str:
    w = WorkspaceClient()
    return f"{w.config.host.rstrip('/')}/api/2.0/genie/spaces/{GENIE_SPACE_ID}"


@tool
def call_genie(question: str) -> str:
    """Send a question to the Genie Space and return the answer or tabular data."""
    headers = _genie_headers()
    base    = _genie_base()

    r = requests.post(f"{base}/start-conversation", headers=headers,
                      json={"content": question}, timeout=30)
    r.raise_for_status()
    d = r.json()
    conv_id, msg_id = d["conversation_id"], d["message_id"]

    poll_url = f"{base}/conversations/{conv_id}/messages/{msg_id}"
    for _ in range(60):
        pr = requests.get(poll_url, headers=headers, timeout=30)
        pr.raise_for_status()
        msg    = pr.json()
        status = msg.get("status", "")

        if status == "COMPLETED":
            for att in msg.get("attachments", []):
                if "text" in att:
                    return att["text"]["content"]
            return "Genie returned no text."

        if status == "EXECUTING_QUERY":
            qr = requests.get(f"{poll_url}/query-result", headers=headers, timeout=30)
            if qr.ok:
                try:
                    sr   = qr.json()["statement_response"]
                    cols = [c["name"] for c in sr["manifest"]["schema"]["columns"]]
                    rows = sr["result"].get("data_array", [])
                    sql  = ""
                    for att in msg.get("attachments", []):
                        if "query" in att:
                            sql = att["query"].get("query", "")
                    return json.dumps({"columns": cols, "rows": rows[:50], "sql": sql})
                except (KeyError, TypeError):
                    pass
            return "Query executed but result could not be parsed."

        if status in ("FAILED", "CANCELED"):
            return f"Genie returned status={status}"
        time.sleep(4)

    return "Genie timed out."


# ── Helpers ──────────────────────────────────────────────────────────────────

def extract_user_query(msgs):   return msgs[-1]["content"]
def extract_chat_history(msgs): return msgs[:-1]

def format_chat_history(msgs):
    history = extract_chat_history(msgs)
    out = []
    for m in history:
        if m["role"] == "user":
            out.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            out.append(AIMessage(content=m["content"]))
    return out

def format_genie_context(x):
    return str(x.get("genie_result", ""))


# ── Prompts ──────────────────────────────────────────────────────────────────

synthesis_prompt = ChatPromptTemplate.from_messages([
    ("system", llm_cfg["synthesis_prompt"]),
    MessagesPlaceholder(variable_name="formatted_chat_history"),
    ("user", "{question}"),
])

rewrite_prompt = PromptTemplate(
    template=llm_cfg["rewrite_prompt"],
    input_variables=["chat_history", "question"],
)

model = ChatDatabricks(
    endpoint=LLM_ENDPOINT,
    extra_params=llm_cfg["llm_parameters"],
)


# ── Chain ────────────────────────────────────────────────────────────────────

chain = (
    {
        "question":              itemgetter("messages") | RunnableLambda(extract_user_query),
        "chat_history":          itemgetter("messages") | RunnableLambda(extract_chat_history),
        "formatted_chat_history":itemgetter("messages") | RunnableLambda(format_chat_history),
    }
    | RunnablePassthrough()
    | {
        "context": RunnableBranch(
            (
                lambda x: len(x["chat_history"]) > 0,
                # Rewrite the question to be self-contained before sending to Genie
                rewrite_prompt | model | StrOutputParser(),
            ),
            itemgetter("question"),
        )
        | {"genie_result": call_genie}
        | RunnableLambda(format_genie_context),
        "formatted_chat_history": itemgetter("formatted_chat_history"),
        "question":               itemgetter("question"),
    }
    | synthesis_prompt
    | model
    | StrOutputParser()
)

mlflow.models.set_model(model=chain)
'''

with open("chain.py", "w") as f:
    f.write(chain_py)

# COMMAND ----------

# ---------------------------------------------------------------------------
# Log the chain with MLflow so it can be deployed to Model Serving
# ---------------------------------------------------------------------------

model_config = mlflow.models.ModelConfig(development_config="genie_rag_config.yaml")

with mlflow.start_run(run_name="genie_rag_chain_v1"):
    logged = mlflow.langchain.log_model(
        lc_model        = os.path.join(os.getcwd(), "chain.py"),
        model_config    = "genie_rag_config.yaml",
        artifact_path   = "chain",
        input_example   = model_config.get("input_example"),
        example_no_conversion = True,
        pip_requirements = [
            "databricks-sdk>=0.20.0",
            "langchain>=0.1.0",
            "langchain-community>=0.0.20",
            "mlflow>=2.10.0",
            "requests>=2.31.0",
            "pyyaml>=6.0",
        ],
    )
    print(f"Model logged: {logged.model_uri}")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Load and test the logged chain
# ---------------------------------------------------------------------------

chain = mlflow.langchain.load_model(logged.model_uri)

test_messages = [
    {"messages": [{"role": "user", "content": "What was total DBU spend last month?"}]},
    # Multi-turn: follow-up references prior answer
    {"messages": [
        {"role": "user",      "content": "What was total DBU spend last month?"},
        {"role": "assistant", "content": "Total DBU spend last month was $45,230."},
        {"role": "user",      "content": "How does that compare to the month before?"},
    ]},
]

for msg in test_messages:
    print(f"\nQ: {msg['messages'][-1]['content']}")
    print(f"A: {chain.invoke(msg)}")
