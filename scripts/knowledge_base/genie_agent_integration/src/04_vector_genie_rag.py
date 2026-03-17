# Databricks notebook source
# src/04_vector_genie_rag.py
#
# Pattern 4: Hybrid Vector Search + Genie RAG Chain
#
# WHY two retrievers instead of one:
#   Genie answers "what does the data say?" (live SQL queries against real tables).
#   Vector Search answers "what does the documentation say?" (PDFs, runbooks, specs).
#   Combined, the LLM can answer questions like:
#     "According to our SLA runbook, are we currently meeting our targets?" →
#       VS finds the SLA definition; Genie queries the actual metrics.
#
# Routing logic:
#   If the question contains data keywords (numbers, trends, comparison, show me)
#   → route to Genie (live data).
#   Otherwise → route to Vector Search (documentation).
#   The chain always passes BOTH results to the synthesis LLM so it can decide
#   which is more relevant.
#
# Production notes:
#   - The Vector Search index must already exist and have documents indexed.
#   - Use databricks-vectorsearch SDK to create the index if needed.
#   - The embedding model (databricks-gte-large-en) is pre-deployed on FMAPI.
#   - MLflow logging is omitted here for brevity; adapt from pattern 3.

# COMMAND ----------

# %pip install -q databricks-sdk databricks-vectorsearch langchain langchain-community mlflow
# dbutils.library.restartPython()

# COMMAND ----------

import json
import time
from operator import itemgetter
from typing import Any, Dict, List

import mlflow
import requests
from databricks.sdk import WorkspaceClient
from databricks.vector_search.client import VectorSearchClient
from langchain.tools import tool
from langchain_community.chat_models import ChatDatabricks
from langchain_community.vectorstores import DatabricksVectorSearch
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough

mlflow.langchain.autolog()

# COMMAND ----------

dbutils.widgets.text("genie_space_id",         "YOUR_SPACE_ID_HERE")
dbutils.widgets.text("llm_endpoint",           "databricks-meta-llama-3-3-70b-instruct")
dbutils.widgets.text("vector_search_endpoint", "one-env-shared-endpoint-5")
dbutils.widgets.text("vector_search_index",    "echostar_db_iceberg.genie_docs.space_doc_index")
dbutils.widgets.text("secret_scope",           "echostar-genie")
dbutils.widgets.text("secret_key",             "api_token")

GENIE_SPACE_ID         = dbutils.widgets.get("genie_space_id")
LLM_ENDPOINT           = dbutils.widgets.get("llm_endpoint")
VS_ENDPOINT            = dbutils.widgets.get("vector_search_endpoint")
VS_INDEX               = dbutils.widgets.get("vector_search_index")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Genie retriever (same low-level client as pattern 2/3)
# ---------------------------------------------------------------------------

def _genie_headers() -> Dict[str, str]:
    w = WorkspaceClient()
    return {"Authorization": f"Bearer {w.config.token}", "Content-Type": "application/json"}


def _genie_base() -> str:
    w = WorkspaceClient()
    return f"{w.config.host.rstrip('/')}/api/2.0/genie/spaces/{GENIE_SPACE_ID}"


def query_genie(question: str, timeout_s: int = 300) -> str:
    """Synchronous Genie query; returns text answer or JSON table."""
    headers = _genie_headers()
    base    = _genie_base()

    r = requests.post(
        f"{base}/start-conversation",
        headers=headers,
        json={"content": question},
        timeout=30,
    )
    r.raise_for_status()
    d       = r.json()
    conv_id = d["conversation_id"]
    msg_id  = d["message_id"]

    poll_url = f"{base}/conversations/{conv_id}/messages/{msg_id}"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        pr = requests.get(poll_url, headers=headers, timeout=30)
        pr.raise_for_status()
        msg    = pr.json()
        status = msg.get("status", "")

        if status == "COMPLETED":
            for att in msg.get("attachments", []):
                if "text" in att:
                    return att["text"]["content"]
            return "No text answer."

        if status == "EXECUTING_QUERY":
            qr = requests.get(f"{poll_url}/query-result", headers=headers, timeout=30)
            if qr.ok:
                try:
                    sr   = qr.json()["statement_response"]
                    cols = [c["name"] for c in sr["manifest"]["schema"]["columns"]]
                    rows = sr["result"].get("data_array", [])
                    sql  = next(
                        (a["query"]["query"] for a in msg.get("attachments", []) if "query" in a),
                        ""
                    )
                    return json.dumps({"columns": cols, "rows": rows[:50], "sql": sql})
                except (KeyError, TypeError):
                    pass
            return "Query result unavailable."

        if status in ("FAILED", "CANCELED"):
            return f"Genie status: {status}"
        time.sleep(4)

    return "Genie timed out."


# COMMAND ----------

# ---------------------------------------------------------------------------
# Vector Search retriever
#
# DatabricksVectorSearch wraps the VS client as a LangChain Retriever.
# The embedding model must match the one used when the index was built.
# ---------------------------------------------------------------------------

vs_client = VectorSearchClient(disable_notice=True)

# Build a LangChain retriever from the VS index
vs_retriever = DatabricksVectorSearch(
    index           = vs_client.get_index(VS_ENDPOINT, VS_INDEX),
    embedding       = None,          # use the index's built-in embedding
    columns         = ["content", "source_url"],
    text_column     = "content",
).as_retriever(search_kwargs={"k": 5, "query_type": "hybrid"})


def format_vs_docs(docs) -> str:
    """Concatenate retrieved document chunks into a single context string."""
    return "\n\n---\n\n".join(
        f"Source: {d.metadata.get('source_url', 'unknown')}\n{d.page_content}"
        for d in docs
    )


# COMMAND ----------

# ---------------------------------------------------------------------------
# Routing: decide whether a question needs live data (Genie) or docs (VS)
#
# This is a simple keyword heuristic. In production, use an LLM router:
#   router_llm.predict("Does this question need live data or documentation?")
# ---------------------------------------------------------------------------

DATA_KEYWORDS = {
    "cost", "spend", "dbu", "usage", "how much", "total", "average",
    "trend", "last month", "last week", "yesterday", "by team", "top",
    "failed", "error", "pipeline", "job", "warehouse", "query",
}


def route_question(inputs: Dict[str, Any]) -> str:
    """Return 'genie' if the question needs live data, else 'vector_search'."""
    q = inputs["question"].lower()
    if any(kw in q for kw in DATA_KEYWORDS):
        return "genie"
    return "vector_search"


# COMMAND ----------

# ---------------------------------------------------------------------------
# Synthesis prompt — always receives BOTH contexts
# ---------------------------------------------------------------------------

synthesis_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a trusted EchoStar platform analyst. "
     "You have been given two sources of information:\n\n"
     "LIVE DATA (from Genie):\n{genie_context}\n\n"
     "DOCUMENTATION (from Vector Search):\n{doc_context}\n\n"
     "Use both sources to answer the question. Prefer live data for numbers/trends. "
     "Prefer documentation for policies/definitions. "
     "Cite your sources explicitly."),
    ("user", "{question}"),
])

model = ChatDatabricks(
    endpoint=LLM_ENDPOINT,
    extra_params={"max_tokens": 1500, "temperature": 0.01},
)


# COMMAND ----------

# ---------------------------------------------------------------------------
# Hybrid chain: both retrievers run in parallel, LLM synthesizes
# ---------------------------------------------------------------------------

hybrid_chain = (
    RunnablePassthrough.assign(
        question=itemgetter("question"),
    )
    | RunnableParallel(
        # Genie always runs (for live data context)
        genie_context=RunnableLambda(lambda x: query_genie(x["question"])),
        # Vector Search always runs (for doc context)
        doc_context=RunnableLambda(lambda x: format_vs_docs(
            vs_retriever.get_relevant_documents(x["question"])
        )),
        question=itemgetter("question"),
    )
    | synthesis_prompt
    | model
    | StrOutputParser()
)


# COMMAND ----------

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

test_questions = [
    # Data question → Genie will have strong signal
    "What is our current weekly DBU cost trend?",
    # Policy question → Vector Search will have strong signal
    "What is our SLA for pipeline recovery after a failure?",
    # Mixed → both sources contribute
    "Are we meeting our SLA for pipeline recovery? Show me the actual failure rates.",
]

for q in test_questions:
    print(f"\n{'='*70}\nQ: {q}\n{'='*70}")
    result = hybrid_chain.invoke({"question": q})
    print(result)
