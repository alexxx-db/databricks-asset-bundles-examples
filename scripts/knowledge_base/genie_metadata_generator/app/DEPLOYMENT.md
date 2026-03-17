# Databricks Apps Deployment Guide

## Quick Fix for Current Error

The error `app exited unexpectedly` was due to a missing entry point. This has been fixed by adding the `command` field to `app.yaml`.

**Note:** Streamlit environment variables like `STREAMLIT_SERVER_PORT` and `STREAMLIT_SERVER_ADDRESS` are [automatically configured](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/system-env#default-environment-variables-for-streamlit) by Databricks Apps, so we don't need to specify them in the command.

## Deployment Options

### Option 1: Deploy from Repository Root (Recommended)

Deploy the entire repository to preserve the template structure:

```bash
# From repository root
databricks apps deploy \
  --source-path . \
  --app-name genie-metadata-generator
```

This ensures the templates at `templates/` and `prompts/` are accessible (both now within the app/ directory).

### Option 2: Deploy App Directory Only

If deploying only the `app/` directory:

1. **Copy templates into app directory:**

```bash
cd app
mkdir -p templates prompts
cp ../src/templates/table_comment_template.yml templates/
cp ../src/templates/genie_space_metadata.yml templates/
# Note: prompts/ directory is now part of the app/ folder
```

2. **Update app.yaml paths:**

```yaml
templates:
  tier1: "templates/table_comment_template.yml"
  tier2: "templates/genie_space_metadata.yml"
  prompt: "prompts/schema_generator_prompt.md"
```

3. **Deploy:**

```bash
databricks apps deploy \
  --source-path app \
  --app-name genie-metadata-generator
```

### Option 3: Templates Not Required (Works with Fallback)

The app will work even without template files - it has built-in fallback prompts. Just deploy and it will use default templates.

## Environment Variables

### Automatically Available in Databricks Apps

According to the [Databricks Apps system environment](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/system-env#default-environment-variables), these are **automatically provided**:

- ✅ `DATABRICKS_HOST` - Workspace URL (auto-set)
- ✅ `DATABRICKS_CLIENT_ID` - Service principal app ID (auto-set)
- ✅ `DATABRICKS_CLIENT_SECRET` - Service principal secret (auto-set)
- ✅ `DATABRICKS_WORKSPACE_ID` - Workspace ID (auto-set)
- ✅ `DATABRICKS_APP_NAME` - App name (auto-set)

### You Need to Configure

Only set this via app.yaml or environment:

```bash
# Required: SQL Warehouse for Unity Catalog queries
DATABRICKS_WAREHOUSE_ID="your-warehouse-id"

# Optional: Override LLM endpoint from app.yaml
LLM_ENDPOINT_NAME="databricks-dbrx-instruct"
```

**Note:** For local development, you still need to set all variables manually in your `.env` file.

## Databricks Apps Configuration

### Step 1: Configure Resources in Databricks Apps UI

When creating or editing your app in Databricks Apps, add the following resources:

**Required Resources**:
1. **SQL Warehouse** (key: `sql-warehouse`)
   - Resource type: SQL Warehouse
   - Permission: Can use
   - Purpose: Unity Catalog queries

2. **Serving Endpoint - Interview** (key: `serving-endpoint`)
   - Resource type: Serving endpoint
   - Endpoint: `databricks-gpt-5-2`
   - Permission: Can query
   - Purpose: Interview questions and planning

3. **Serving Endpoint - Summarizer** (key: `serving-endpoint-2`)
   - Resource type: Serving endpoint
   - Endpoint: `databricks-gemini-2-5-flash`
   - Permission: Can query
   - Purpose: Context summarization for large schemas

**Optional Resources**:
4. **Lakebase Database** (key: `database`)
   - Resource type: Lakebase database
   - Permission: Can connect and create
   - Purpose: Session persistence and YAML library

### Step 2: Update app.yaml

The `app.yaml` maps these resources to environment variables:

```yaml
# Environment variables from app resources
env:
  - name: LLM_ENDPOINT_NAME
    valueFrom: serving-endpoint
  - name: SUMMARIZER_ENDPOINT_NAME
    valueFrom: serving-endpoint-2

resources:
  - name: default
    warehouse_id: "your-warehouse-id"  # Your SQL Warehouse ID

config:
  llm:
    # Main interview endpoint (GPT-5.2) - overridden by env var
    endpoint_name: "databricks-gpt-5-2"
    max_tokens: 2048
    temperature: 0.7
    
    # Summarizer endpoint (Gemini Flash) - overridden by env var
    summarizer_endpoint_name: "databricks-gemini-2-5-flash"
    summarizer_max_tokens: 8192
    summarizer_temperature: 0.3
```

**Resource Key Benefits**:
- Secure: Endpoint names come from resource configuration
- Portable: Same code works across environments
- Flexible: Change endpoints without code changes

## Troubleshooting

### Error: "app exited unexpectedly"
- ✅ **Fixed** - Added `command` field to app.yaml
- Redeploy after pulling latest changes

### Error: "Template files not found"
- App will work with fallback templates
- Or follow Option 2 above to copy templates

### Error: "Connection failed"
- Check environment variables are set
- Verify service principal has Unity Catalog permissions
- Ensure SQL Warehouse is running

### Error: "LLM endpoint not found"
- Check `endpoint_name` in app.yaml
- Verify endpoint is enabled in workspace
- Try default: `databricks-dbrx-instruct`

## Post-Deployment

1. **Access the app** at the Databricks Apps URL
2. **Test connection** by browsing catalogs
3. **Run interview** on a test table
4. **Verify YAML** generation works

## Updating the App

```bash
# Pull latest changes
git pull

# Redeploy
databricks apps deploy \
  --source-path . \
  --app-name genie-metadata-generator
```

## Using Databricks Asset Bundles (DABs)

Create `databricks.yml` in repository root:

```yaml
bundle:
  name: genie-metadata-generator

resources:
  apps:
    genie_metadata_generator:
      name: genie-metadata-generator
      source_code_path: ./app
      
targets:
  dev:
    resources:
      apps:
        genie_metadata_generator:
          config:
            sql_warehouse:
              warehouse_id: ${var.dev_warehouse_id}
  
  prod:
    resources:
      apps:
        genie_metadata_generator:
          config:
            sql_warehouse:
              warehouse_id: ${var.prod_warehouse_id}
```

Deploy with:

```bash
databricks bundle deploy -t prod
```

## Complete Deployment Checklist

- [ ] Latest code pulled
- [ ] `app.yaml` updated with your warehouse ID
- [ ] Environment variables configured
- [ ] Service principal has Unity Catalog access
- [ ] SQL Warehouse is running
- [ ] LLM endpoint is available
- [ ] Templates accessible (or using fallback)
- [ ] App deployed successfully
- [ ] Can browse catalogs
- [ ] Interview generates YAML
- [ ] Download works

## Next Steps

After successful deployment:

1. Share app URL with team
2. Document table using the app
3. Test generated YAML with Genie
4. Iterate on prompts if needed
5. Scale to more tables

## Support

For issues:
1. Check [TESTING.md](TESTING.md) for troubleshooting
2. Review [README.md](README.md) for usage
3. Check Databricks Apps logs
4. Verify environment configuration
