# genie_agent_integration — Genie Space as an Agent Tool

Five progressive patterns for wrapping a Databricks Genie Space as a
callable AI agent component.

## Patterns

| # | File | Pattern | When to use |
|---|------|---------|-------------|
| 1 | `01_uc_function_tool.py` | UC Python function | SQL analysts; AI_QUERY() pipelines; UC RBAC |
| 2 | `02_langchain_agent.py` | LangChain BaseTool + REACT agent | Multi-tool reasoning; autonomous routing |
| 3 | `03_genie_rag_chain.py` | Genie-as-retriever RAG (MLflow logged) | Production chatbots; Model Serving deployment |
| 4 | `04_vector_genie_rag.py` | Hybrid Vector Search + Genie | Mixed doc+data questions |
| 5 | `05_stateful_conversations.py` | Per-user stateful conversations | Multi-user Apps; follow-up queries with context |

## Key design decisions

### Why the Genie API is async (and what that means for your code)

The Genie API is asynchronous:
1. `POST /start-conversation` → returns `{conversation_id, message_id}` immediately
2. `GET /conversations/{id}/messages/{msg_id}` → poll until status is terminal
3. Status `EXECUTING_QUERY` means Genie ran SQL; fetch the result from `/query-result`
4. Status `COMPLETED` means Genie returned a text answer (no SQL)

All patterns implement this polling loop. The timeout is 300s (5 min) by default.

### Per-user conversation isolation (Pattern 5)

Sharing a single `conversation_id` across users means Genie mixes contexts:
- Alice asks about Q1; Bob asks about Q2; Alice's follow-up gets Q2 context
- Always maintain a `Dict[user_id → conversation_id]` and scope it per user

### Genie API base URL

```
https://<workspace-host>/api/2.0/genie/spaces/<space_id>/start-conversation
https://<workspace-host>/api/2.0/genie/spaces/<space_id>/conversations/<conv_id>/messages
https://<workspace-host>/api/2.0/genie/spaces/<space_id>/conversations/<conv_id>/messages/<msg_id>/query-result
```

### MLflow logging (Pattern 3)

The RAG chain is logged as an MLflow model so it can be:
- Registered in Unity Catalog Model Registry
- Deployed to Model Serving for low-latency inference
- Evaluated with `mlflow.evaluate()` against a golden dataset

## Secrets

Some tasks (e.g. **Pattern 1 — UC function**) accept `secret_scope` and `secret_key` as job parameters or notebook widgets. These must point to an existing Databricks secret scope and key that holds the **Genie API token** (or workspace PAT) used to call the Genie API. Create the scope and store the token before running; never log or commit the token. See [Databricks secrets](https://docs.databricks.com/security/secrets/secret-scopes.html) for how to create scopes and keys.

## Quick start

```bash
databricks bundle deploy --target dev
databricks bundle run genie_agent_demo \
  -p genie_space_id=<your-space-id> \
  -p llm_endpoint=databricks-meta-llama-3-3-70b-instruct
```

To run individual patterns:
```bash
databricks bundle run genie_agent_demo --task register_uc_function
databricks bundle run genie_agent_demo --task langchain_agent
databricks bundle run genie_agent_demo --task genie_rag_chain
databricks bundle run genie_agent_demo --task vector_genie_rag
databricks bundle run genie_agent_demo --task stateful_conversations
```
