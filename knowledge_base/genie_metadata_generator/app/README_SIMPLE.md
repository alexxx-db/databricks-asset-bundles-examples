# Description Agent - Simplified UI

AI-powered description generator for Databricks Unity Catalog tables and columns, powered by Genify's robust backend.

---

## Overview

Description Agent combines a simple, focused UI with Genify's powerful backend capabilities:

- **Simple UI**: Two-mode interface ("Get me started" / "Check my work")
- **Powerful Backend**: Genify's LLM clients, data profiling, and authentication
- **Optional Data Profiling**: Checkbox to include automated table/column statistics
- **Direct SQL Application**: Generate and execute `COMMENT ON` statements

---

## Features

### Get Me Started Mode
- Generate initial descriptions from conceptual information
- Optional data profiling for enhanced context
- AI-powered description generation using GPT-5.2
- Editable output before applying to catalog

### Check My Work Mode
- Review existing descriptions for quality and completeness
- Optional data profiling to validate against actual data
- AI-powered suggestions for improvements
- Side-by-side comparison of original and improved versions

### Data Profiling (Optional)
When enabled via checkbox, the app automatically profiles your table to provide:
- Row counts, table size, format
- Column distributions and statistics
- Date ranges and recency
- Top values for categorical columns
- Null percentages and data completeness

This profile data is included in the LLM context for more accurate descriptions.

---

## Architecture

```
Description Agent (Simple UI)
├── app_simple.py          # Streamlit UI with two modes
├── app_simple.yaml        # App configuration
└── Backend (from Genify):
    ├── llm/               # LLM clients (GPT-5.2)
    ├── data/              # Profiling & information_schema
    ├── auth/              # Service principal auth
    ├── state/             # State management & services
    └── config.py          # Configuration management
```

---

## Quick Start

### Prerequisites

- Databricks workspace with Unity Catalog
- SQL Warehouse for queries
- Service principal with appropriate permissions

### Local Development

```bash
# Set environment variables
export DATABRICKS_HOST="your-workspace.cloud.databricks.com"
export DATABRICKS_WAREHOUSE_ID="your-warehouse-id"
export DATABRICKS_CLIENT_ID="your-service-principal-id"
export DATABRICKS_CLIENT_SECRET="your-service-principal-secret"

# Run the app
streamlit run app_simple.py
```

### Deploy to Databricks Apps

```bash
# Upload to workspace
databricks workspace import-dir . /Workspace/Users/your.email@databricks.com/apps/description-agent --profile your-profile --overwrite

# Deploy
databricks apps deploy description-agent --source-code-path /Workspace/Users/your.email@databricks.com/apps/description-agent --profile your-profile
```

---

## Configuration

All settings are in `app_simple.yaml`:

```yaml
# LLM Configuration
llm:
  endpoint_name: "databricks-gpt-5-2"
  max_tokens: 2048
  temperature: 0.7

# SQL Warehouse
sql_warehouse:
  warehouse_id: "your-warehouse-id"

# Lakebase (disabled for simplified app)
lakebase:
  enabled: false
```

---

## Usage

### 1. Get Me Started

1. Enter table name (e.g., `catalog.schema.table`)
2. Optionally enter column name (leave blank for table-level)
3. Provide information/context about the data asset
4. Optionally check "Profile my data" for automated statistics
5. Click "Generate Description"
6. Review and edit the generated description
7. Click "Apply description" to execute `COMMENT ON` SQL

### 2. Check My Work

1. Enter table name
2. Optionally enter column name
3. Paste existing description
4. Optionally check "Profile my data"
5. Click "Review Description"
6. Review AI feedback and suggested improvements
7. Edit the improved description as needed
8. Click "Apply description" to update the catalog

---

## Permissions Required

The app's service principal needs:

```sql
-- Catalog permissions
GRANT USE CATALOG ON CATALOG your_catalog TO `service-principal-id`;
GRANT MODIFY ON CATALOG your_catalog TO `service-principal-id`;

-- Schema permissions
GRANT USE SCHEMA ON SCHEMA your_catalog.your_schema TO `service-principal-id`;
GRANT MODIFY ON SCHEMA your_catalog.your_schema TO `service-principal-id`;

-- Table permissions (for each table)
GRANT SELECT ON TABLE your_catalog.your_schema.your_table TO `service-principal-id`;
GRANT MODIFY ON TABLE your_catalog.your_schema.your_table TO `service-principal-id`;
```

---

## Technical Details

### LLM Integration

Uses Genify's `get_main_llm_client()` which provides:
- Automatic OAuth handling via Databricks SDK
- Retry logic with exponential backoff
- Comprehensive request/response logging
- Rate limit management

### Data Profiling

Leverages Genify's profiling service:
- Lightweight statistics from cached metadata
- Smart sampling for large tables
- Type-specific profiling (numeric, categorical, date, boolean)
- Formatted output optimized for LLM context

### State Management

Simplified session state:
- No persistent storage (Lakebase disabled)
- In-memory session state via Streamlit
- Suitable for single-session workflows

---

## Differences from Full Genify

| Feature | Description Agent | Full Genify |
|---------|------------------|-------------|
| UI Complexity | Simple two-mode | Multi-step workflow |
| Data Profiling | Optional checkbox | Integrated step |
| Session Persistence | In-memory only | Lakebase PostgreSQL |
| Metadata Output | Direct SQL only | YAML + SQL + Library |
| Interview Style | Single prompt | Multi-section interview |
| Genie Space Config | Not included | Full support |

---

## Troubleshooting

### "Profile my data" fails

**Possible causes:**
- Table doesn't exist or is not accessible
- Warehouse permissions issue
- Table has no data or unsupported column types

**Solutions:**
- Verify table name format: `catalog.schema.table`
- Check service principal has `SELECT` permission
- Try without profiling first

### LLM request fails

**Possible causes:**
- Endpoint not available
- Rate limits exceeded
- Network/auth issues

**Solutions:**
- Verify `endpoint_name` in `app_simple.yaml`
- Check Foundation Models API is enabled
- Wait a moment and retry (automatic exponential backoff)

### Cannot apply description

**Possible causes:**
- Missing `MODIFY` permissions
- Invalid table/column name
- SQL syntax error

**Solutions:**
- Grant `MODIFY` on catalog, schema, and table
- Verify table name matches format
- Check generated SQL for issues

---

## Support

For issues or questions:
1. Check application logs in Databricks Apps console
2. Verify environment configuration in `app_simple.yaml`
3. Review [Genify documentation](README.md) for backend details
4. Check Databricks Apps [documentation](https://docs.databricks.com/dev-tools/databricks-apps/)

---

## References

- [Databricks Apps Documentation](https://docs.databricks.com/dev-tools/databricks-apps/)
- [Unity Catalog COMMENT ON](https://docs.databricks.com/sql/language-manual/sql-ref-syntax-ddl-comment)
- [Information Schema](https://docs.databricks.com/sql/language-manual/sql-ref-information-schema)
- [Foundation Models API](https://docs.databricks.com/machine-learning/foundation-models/)
- [Genify README](README.md) (Full application)

