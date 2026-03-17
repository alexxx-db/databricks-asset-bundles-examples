# Genie Spaces Example: Testing & Validation Plan

This document describes how to test and validate the Genie Spaces deployment example included in this repository. It ensures you can confidently create, update, and manage Genie Spaces using Databricks Asset Bundles (DABs) and the Genie Management API.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Script Testing](#local-script-testing)
- [Bundle Job Testing](#bundle-job-testing)
- [Error Handling & Edge Case Testing](#error-handling--edge-case-testing)
- [Validation Checklist](#validation-checklist)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

1. **Databricks SDK for Python**
   ```bash
   pip install databricks-sdk
   ```

2. **Databricks CLI**
   ```bash
   databricks configure --token
   ```

3. **Genie Management API permissions** for your Databricks workspace user or service principal.

4. **Valid warehouse ID and workspace access.**

---

## Local Script Testing

### 1. Prepare Environment Variables

Set the required variables before running the deployment script:

```bash
export WAREHOUSE_ID="<your-warehouse-id>"
export GENIE_SPACE_CONFIG_PATH="genie_spaces/billing_assistant.json"
```

### 2. Run Deployment Script

Run the script directly to deploy the Genie Space:

```bash
python deployment/deploy_genie_space.py
```

### 3. Expected Output

- INFO logs confirming the config is loaded and deployment started.
- Success message upon Genie Space creation or update.
- Error logs if anything fails (missing vars, API error, etc).

### 4. Validation

- Log in to your Databricks workspace.
- Navigate to Genie Spaces.
- Confirm the Genie Space with the configured title exists with the defined properties.

---

## Bundle Job Testing

### 1. Confirm Bundle Variables

Ensure `bundle.yml` has the correct variables:

```yaml
variables:
  warehouse_id: "<your-warehouse-id>"
  target_catalog: "<your-catalog>"
```

### 2. Trigger DAB Job

Use CLI or Databricks UI to deploy:

```bash
databricks bundle deploy
```

### 3. Inspect Job Results

- Review job logs for success, warnings, or errors.
- Check Genie Space status in Databricks Workspace.

---

## Error Handling & Edge Case Testing

### 1. Missing Config File

- Rename or delete `genie_spaces/billing_assistant.json`
- Run the script
- Script should log a config error and exit with no space created/updated.

### 2. Missing Environment Variable

- Unset `WAREHOUSE_ID` before running the script
- Expect a logged error and halted execution.

### 3. API Error Simulation

- Use invalid workspace/token in your environment
- Script should produce detailed error logs (authentication, API issue).

---

## Validation Checklist

- [ ] Genie Space created or updated as per JSON config.
- [ ] Deployment script outputs clear logs (success/failure).
- [ ] Proper handling of missing configs/environment variables.
- [ ] Changes confirmed in Databricks Workspace UI or via API.
- [ ] DAB job integration deploys with correct parameterization.
- [ ] Edge cases and errors trigger clear messages and safe exits.

---

## Troubleshooting

- Review script logs for missing configs or env vars.
- Check your Databricks credentials and workspace permissions.
- Validate Genie Management API access and tokens.
- For API failures, confirm your workspace URL, user permissions, and network connectivity.

---

**If you face errors, share log output with your team or in a GitHub issue for support. For additional help, consult the README or open a discussion!**
