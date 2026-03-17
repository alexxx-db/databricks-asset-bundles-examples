# Contributing to bundle-examples

Thanks for your interest in contributing. This document points you to the right places and practices.

## Repository layout

- **Canonical examples** live at the repo root: `knowledge_base/`, template-generated dirs (`default_python/`, etc.), and `contrib/`.
- The `scripts/` directory may contain tooling or a mirror; when in doubt, use paths from the root. CI discovers all bundle directories via `scripts/discover_bundle_dirs.py`.

See the main [README](README.md) for an overview of template-generated projects and knowledge base examples.

## Security and secrets

- **Never commit credentials.** Use [Databricks secret scopes](https://docs.databricks.com/security/secrets/secret-scopes.html) or environment variables for API keys, tokens, and passwords.
- When adding or changing examples that use secrets, document the required scope and key names in that example’s README.
- For SQL or shell usage, validate/sanitize user or UI-derived identifiers and arguments to prevent injection. See [docs/CODEBASE_REVIEW_AND_RECOMMENDATIONS.md](docs/CODEBASE_REVIEW_AND_RECOMMENDATIONS.md) for patterns used in this repo.

## Code quality and tests

- **Linting:** From the repo root, run `ruff check .` (config in `pyproject.toml`). CI runs ruff on a subset of paths; see [README – Code quality](README.md#code-quality).
- **Type checking:** Optional `pyright` from the repo root.
- **Tests:** See [README – Running tests](README.md#running-tests) for how to run pytest for identifier validation, add_asset, iceberg_catalog, and mlops_stacks.
- **Bundles:** Ensure every new or modified bundle has a valid `databricks.yml` with `bundle.name`. CI runs `databricks bundle validate` for all discovered bundles.

## Local bundle validation

To validate all bundles locally (same logic as CI, no workspace auth required):

```bash
export DATABRICKS_HOST=https://placeholder.databricks.com
for dir in $(python scripts/discover_bundle_dirs.py); do
  (cd "$dir" && databricks bundle validate -t dev) || exit 1
done
```

Or run: `./scripts/local_bundle_validate.sh`

## Pull requests

- Open a PR against `main` (or the default branch). CI will run yamllint, Python syntax checks, bundle schema validation, README checks, template drift, bundle validate for all bundles, and ruff.
- For larger or structural changes, consider referencing [docs/CODEBASE_REVIEW_AND_RECOMMENDATIONS.md](docs/CODEBASE_REVIEW_AND_RECOMMENDATIONS.md) so reviewers can align with existing hardening and patterns.
