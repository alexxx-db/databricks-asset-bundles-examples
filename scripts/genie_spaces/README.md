# Databricks Asset Bundles Examples: Genie Spaces CI/CD Integration

## Overview

This repository provides comprehensive examples and patterns for using [Databricks Asset Bundles (DABs)](https://docs.databricks.com/en/dev-tools/asset-bundles.html) to automate the deployment and management of Genie Spaces via the [Genie Management API](https://docs.databricks.com/en/genie/index.html), enabling robust CI/CD workflows, source-controlled configurations, and scalable space promotion across environments.

The main production-ready example demonstrates how to:

- Version Genie Space configurations as code.
- Deploy and update Genie Spaces programmatically using Databricks SDK and the Genie Management API.
- Integrate deployment into DAB pipeline jobs for automated CI/CD.

---

## Table of Contents

- [Features](#features)
- [Repository Structure](#repository-structure)
- [Genie Spaces Deployment Workflow](#genie-spaces-deployment-workflow)
- [Requirements](#requirements)
- [Setup Instructions](#setup-instructions)
- [Usage Guide](#usage-guide)
- [Extending This Example](#extending-this-example)
- [Troubleshooting & Common Issues](#troubleshooting--common-issues)
- [Security Notes](#security-notes)
- [References](#references)

---

## Features

- **Version-Controlled Genie Spaces**  
  All Genie Space definitions live as JSON files under `genie_spaces/`, supporting traceability, review, and promotion across environments.

- **API-Driven CI/CD Deployment**  
  Orchestrates deployment via DAB-managed jobs, using Python scripts and the Databricks SDK for create/update operations against Genie Spaces.

- **Parameterization and Environment Awareness**  
  Dynamically injects environment-specific variables (e.g., catalog, warehouse) using Databricks bundle variables and job widgets.

- **Production-grade Implementation**  
  Error handling, logging, input validation, and extensibility for real-world deployment scenarios.

---

## Repository Structure

```
alexxx-db/databricks-asset-bundles-examples/
├── bundle.yml                   # DAB job definitions, bundle variables
├── README.md                    # This documentation
├── deployment/
│   └── deploy_genie_space.py    # Production-ready deployment script
└── genie_spaces/
    └── billing_assistant.json   # Example Genie Space configuration
```

---

## Genie Spaces Deployment Workflow

1. **Define Genie Space Configuration**
   - Create or edit JSON files in `genie_spaces/` describing your Genie Space.
   
2. **Configure Deployment Parameters**
   - Set variables such as `warehouse_id` and `target_catalog` in `bundle.yml`.

3. **Orchestrate Deployment via DAB Job**
   - Include a job in `bundle.yml` that runs the deployment script.

4. **Run Deployment Script**
   - The job executes `deployment/deploy_genie_space.py`, which uses the Databricks SDK to interact with the Genie Management API.

5. **Promotion & Rollback**
   - Genie Spaces can be promoted across environments or restored from version-controlled configurations.

---

## Requirements

- **Databricks CLI**
- **Databricks SDK for Python**
- **Genie Management API access/permissions**
- **Valid Databricks workspace, cluster, and warehouse**
- **DAB-compatible Databricks environment**

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/alexxx-db/databricks-asset-bundles-examples.git
cd databricks-asset-bundles-examples
```

### 2. Install Dependencies

Ensure the Databricks SDK and CLI are installed:

```bash
pip install databricks-sdk
databricks configure
```

### 3. Configure Genie Space(s)

Edit or add Genie Space definitions in `genie_spaces/` (format example provided below).

### 4. Set Bundle Variables

Update `bundle.yml` with your deployment-specific values:

```yaml
variables:
  warehouse_id: "<your-warehouse-id>"
  target_catalog: "<your-catalog>"
```

### 5. Review Deployment Script

Check `deployment/deploy_genie_space.py` for compatibility with your environment, authentication, and logging preferences.

---

## Usage Guide

### 1. Genie Space JSON Configuration Example

```json
{
  "title": "Billing Assistant",
  "description": "Genie Space for billing-related analytic tasks.",
  "instructions": "Use this space to run analysis and queries on billing data.",
  "benchmarks": [],
  "table_references": {},
  "example_queries": [],
  "joins": [],
  "warehouse_id": ""
}
```

### 2. Databricks Asset Bundle (`bundle.yml`) Example

```yaml
resources:
  jobs:
    deploy_genie_spaces:
      name: "deploy-genie-spaces-${bundle.target}"
      tasks:
        - task_key: upsert_genie_space
          notebook_task:
            notebook_path: ./deployment/deploy_genie_space.py

variables:
  warehouse_id: ""
  target_catalog: ""
```

### 3. Deployment Script (`deployment/deploy_genie_space.py`)

- Handles configuration loading, workspace client creation, environment variable injection, creation/update logic, error handling, and logging.
- Accepts and validates `target_catalog` and `warehouse_id` via Databricks job widgets for runtime parameterization.

---

## Extending This Example

- Add more Genie Space JSON configs under `genie_spaces/`.
- Provide additional Python scripts for bulk deployment, rollback, or migration logic.
- Customize success/failure notifications or integrate with Databricks workflows (e.g., webhooks, alerts).

---

## Troubleshooting & Common Issues

- **Missing or invalid config:**  
  Ensure your JSON config is present and correctly structured in `genie_spaces/`.

- **Insufficient permissions:**  
  Confirm Genie Management API access for your workspace user/service principal.

- **API authentication failures:**  
  Validate Databricks SDK and CLI authentication prior to job runs.

- **Unset variables:**  
  Bundle/Job variables like `warehouse_id` and `target_catalog` must be set in `bundle.yml` or provided to the job at runtime.

- **Network/API errors:**  
  Check logs produced by `deploy_genie_space.py` for diagnostic info.

---

## Security Notes

- **Keep credentials secure:**  
  Never commit API tokens or secrets to version control; use Databricks Secret Scope or environment variables for sensitive info.

- **Role-based access:**  
  Ensure principle of least privilege in workspace and Genie API permissions.

---

## References

- [Databricks Asset Bundles Documentation](https://docs.databricks.com/en/dev-tools/asset-bundles.html)
- [Genie Management API Documentation](https://docs.databricks.com/en/genie/index.html)
- [Databricks SDK for Python](https://github.com/databricks/databricks-sdk-python)
- [Databricks CLI](https://docs.databricks.com/en/dev-tools/cli/index.html)

---

## License

See [LICENSE](LICENSE) for terms.

---

**For questions, feature requests, or issues, please open a GitHub issue or pull request.**