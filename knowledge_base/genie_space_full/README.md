# genie_space_full — Genie Space Full Lifecycle Bundle

Complete example of managing a Databricks Genie Space through the full
deploy → use → sync-back-to-git lifecycle using Databricks Asset Bundles.

## Why jobs instead of native resources

Genie Spaces are **not** a native DAB resource type (as of CLI 0.263+).
The only supported pattern is a notebook task that calls the Genie Management
API (`w.genie.create_space` / `update_space`).  State (the space ID) is stored
in a workspace file **outside** the bundle sync directory so `bundle deploy`
does not delete it on subsequent runs.

## DABs known bugs / workarounds demonstrated here

| Bug | Workaround |
|-----|-----------|
| `presets.name_prefix` not applied to `apps` resources (GitHub #3131, closed "not planned") | Embed `${bundle.target}` directly in `app.name` |
| `tags` field silently dropped on `app` resource type | Apply tags to `jobs`/`pipelines` only; Apps REST API does not support them |
| Genie API slug is `genie` not `genie-spaces` | All permission calls use `/api/2.0/permissions/genie/{space_id}` |

## Resources deployed

| Resource | Type | Purpose |
|----------|------|---------|
| `genie-space-full-deploy-{target}` | Job | Create or update the Genie Space from JSON config |
| `genie-space-full-sync-{target}` | Job | Read live SME edits from workspace and commit to git |
| `genie-space-full-permissions-{target}` | Job | PATCH `/api/2.0/permissions/genie/{space_id}` to grant ACLs |
| `genie-qa-reviewer-{target}` | App | Streamlit app: re-execute any conversation's SQL under app SP identity |

## Quick start

```bash
# 1. Deploy all resources
databricks bundle deploy --target dev

# 2. Run the deploy job to create/update the Genie Space
databricks bundle run deploy_genie_space

# 3. Copy the space_id from the job output and wire it in:
databricks bundle deploy --target dev --var space_id=<id>
# This enables the QA Reviewer app and permissions job to reference the space.

# 4. Set permissions (grant read to a group):
databricks bundle run set_genie_permissions \
  -p read_groups=finops-team \
  -p manage_groups=data-platform

# 5. After SMEs edit the space in the UI, sync back to git (with PR):
databricks bundle run sync_genie_space \
  -p space_name=echostar_finops \
  -p create_review=true
```

## File layout

```
genie_space_full/
├── databricks.yml                    # Bundle root — variables & targets
├── resources/
│   └── genie_space_full.yml          # Jobs + App resource definitions
├── src/
│   ├── deploy_genie_space.py         # Create/update via Genie API (idempotent)
│   ├── sync_genie_space.py           # Read live state → commit to GitHub/GitLab
│   └── set_genie_permissions.py      # PATCH /api/2.0/permissions/genie/{id}
├── genie_spaces/
│   └── echostar_finops.json          # Serialized space definition (EchoStar FinOps)
└── app/
    ├── app.py                        # Streamlit QA Reviewer
    ├── app.yml                       # App entrypoint config
    └── requirements.txt
```

## Genie space permissions API

```
GET  /api/2.0/permissions/genie/{space_id}   → current ACL
PATCH /api/2.0/permissions/genie/{space_id}  → add ACL entries
```

Valid `permission_level` values: `CAN_READ`, `CAN_RUN`, `CAN_EDIT`, `CAN_MANAGE`.

## Space JSON format

`genie_spaces/echostar_finops.json` is the EchoStar-themed example covering:
- FinOps DBU usage (`workspace_dbu_daily`)
- Pipeline run costs (`pipeline_runs`)
- SQL warehouse usage (`sql_warehouse_usage`)
- Sample questions, example SQL Q&A pairs, join specs, and text instructions
