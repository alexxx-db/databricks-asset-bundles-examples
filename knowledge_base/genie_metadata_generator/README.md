# genie_metadata_generator (Genify) — AI-Powered Genie Space Metadata

Deploys the **Genify** Databricks App: an AI interview tool that generates
production-quality Genie Space metadata by conducting a structured LLM
interview with data owners.

## Why this exists

Genie Spaces require rich metadata to answer questions accurately:
- **Text instructions** — tell Genie which columns mean what, how to handle
  edge cases, what business terms map to which SQL expressions
- **Example SQL Q&A pairs** — training signal for Genie's query generation
- **SQL expressions** — reusable metrics and filters in the Knowledge Store
- **Clarification rules** — when to ask the user for more detail

Writing this metadata manually is slow and inconsistent. Genify automates it
via a structured LLM interview, guided by table profiles from `ANALYZE TABLE`
and Unity Catalog `information_schema`.

## Architecture

```
Streamlit App (Databricks Apps)
│
├── Table Browser        ← UC information_schema + DESCRIBE EXTENDED
├── Data Profiler        ← row counts, cardinality, null rates, samples
├── Context Summarizer   ← Gemini Flash compresses large schemas for GPT context
├── Section Interview    ← GPT conducts structured interview (5 sections)
│     ├── sql_expressions        (Genie Knowledge Store entries)
│     ├── query_instructions     (how to handle time, aggregations, status)
│     ├── example_queries        (Q&A pairs with SQL)
│     ├── clarification_rules    (when Genie should ask for more info)
│     └── space_context          (defaults, scope, hidden columns)
├── YAML Editor          ← review / edit generated YAML before applying
├── Export Panel         ← copy YAML / apply directly to Genie space
└── Session Persistence  ← in-memory (dev) or Lakebase PostgreSQL (prod)
```

## Two session backends

| Backend | Config | Use case |
|---------|--------|---------|
| In-memory | `lakebase_enabled=false` (default) | Dev; sessions lost on restart |
| Lakebase (PostgreSQL) | `lakebase_enabled=true` | Prod; sessions survive restarts; multi-device |

The Lakebase schema is created by the `genify_lakebase_migration` job.

## Two LLM endpoints

| Variable | Default | Role |
|----------|---------|------|
| `LLM_ENDPOINT_NAME` | `databricks-gpt-5-2` | Interview LLM — asks questions, generates YAML |
| `SUMMARIZER_ENDPOINT_NAME` | `databricks-gemini-2-5-flash` | Compresses large table schemas before sending to GPT |

Why two: GPT-5.2 has a 400K input context limit but tables with 100+ columns
can overflow it. Gemini Flash (1M context) summarizes the profile first.

## DABs notes

- **`presets.name_prefix` NOT applied to Apps** (GitHub #3131, closed "not planned").
  Workaround: embed `${bundle.target}` directly in `app.name`.
- **`tags` silently dropped** on App resources. Tag the jobs instead.
- App source code is referenced via `source_code_path: ./app`. DABs syncs the
  entire `app/` directory to the workspace.

## File layout

```
genie_metadata_generator/
├── databricks.yml
├── resources/
│   └── genie_metadata_generator.yml   # App + migration job + batch job
├── app/                               # Full Genify Streamlit source
│   ├── app.py                         # Main entrypoint
│   ├── app.yaml                       # Databricks App config (command, resources, env)
│   ├── config.py                      # AppConfig — reads app.yaml + env vars
│   ├── auth/                          # Service principal + OAuth OBO auth
│   ├── data/                          # Table profiler, information_schema client
│   ├── llm/                           # LLM client + section-based interview engine
│   ├── state/                         # Session state (in-memory + Lakebase backends)
│   │   ├── backends/                  # base, lakebase, session backends
│   │   └── services/                  # catalog, interview, library, profile services
│   ├── ui/                            # Streamlit page components
│   │   ├── table_browser.py           # Browse UC catalogs/schemas/tables
│   │   ├── split_screen_interview.py  # Side-by-side table profile + interview
│   │   ├── yaml_editor_page.py        # YAML review and edit
│   │   ├── export_panel.py            # Copy/apply to Genie space
│   │   └── review_panel.py            # Pre-apply review
│   ├── templates/
│   │   ├── genie/                     # 5-section Genie metadata template
│   │   └── table_comment/             # 5-section UC table comment template
│   └── utils/                         # YAML utils, data conversion, decorators
├── notebooks/
│   ├── run_lakebase_migration.py      # Create genify.user_sessions in PostgreSQL
│   └── batch_generate_metadata.py     # Headless bulk metadata generation
└── migrations/
    └── 001_create_sessions_table.sql  # PostgreSQL DDL for session persistence
```

## Quick start

```bash
# Deploy app + supporting jobs
databricks bundle deploy --target dev

# (Prod only) Run Lakebase migration once
databricks bundle run genify_lakebase_migration

# Access the app
databricks apps get genify-dev   # shows the app URL

# Headless batch generation (bootstrap metadata for an entire schema)
databricks bundle run genify_batch_generate \
  -p uc_catalog=example_catalog \
  -p uc_schema=finops \
  -p output_catalog=example_catalog \
  -p output_schema=genie_metadata
```

## Section-based interview template

The Genie metadata interview covers 5 sections (from `app/templates/genie/sections.yaml`):

| Section | File | Contents |
|---------|------|---------|
| SQL Expressions | `01_sql_expressions.yml` | Reusable metrics, filters, dimensions for Knowledge Store |
| Query Instructions | `02_query_instructions.yml` | Time-based queries, aggregations, status filtering |
| Example Queries | `03_example_queries.yml` | 5–10 Q&A pairs with SQL |
| Clarification Rules | `04_clarification_rules.yml` | When Genie should ask for more info |
| Space Context | `05_space_context.yml` | Defaults, scope, hidden columns |
