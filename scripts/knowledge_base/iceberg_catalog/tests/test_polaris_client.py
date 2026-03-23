"""
tests/test_polaris_client.py
============================
Unit tests for PolarisClient using `responses` to mock HTTP calls.

We test:
  - OAuth token fetch and in-process cache
  - list_namespaces / list_tables / load_table happy paths
  - HTTP error propagation (4xx, 5xx)
  - Token refresh when near-expiry
"""

from __future__ import annotations

import time

import pytest
import responses as resp_lib

from iceberg_catalog.polaris_client import IcebergTableSummary, PolarisClient

# ── Fixtures ──────────────────────────────────────────────────────────────────

ACCOUNT       = "example.us-west-2.aws"
REST_URI      = f"https://{ACCOUNT}.snowflakecomputing.com/polaris/api/catalog"
TOKEN_URI     = f"https://{ACCOUNT}.snowflakecomputing.com/oauth/token"
CATALOG       = "ICEBERG_LAKEHOUSE"
CATALOG_LOWER = CATALOG.lower()


def _make_client() -> PolarisClient:
    return PolarisClient(
        rest_uri       = REST_URI,
        token_endpoint = TOKEN_URI,
        client_id      = "test_client_id",
        client_secret  = "test_client_secret",
        principal_role = "databricks_svc_role",
        catalog_name   = CATALOG,
        timeout_seconds = 5,
    )


def _register_token(ttl: int = 3600) -> None:
    resp_lib.add(
        resp_lib.POST,
        TOKEN_URI,
        json={"access_token": "test_token_abc123", "expires_in": ttl, "token_type": "Bearer"},
        status=200,
    )


# ── Token tests ───────────────────────────────────────────────────────────────

@resp_lib.activate
def test_token_is_fetched_on_first_call() -> None:
    _register_token()
    client = _make_client()
    token = client._get_token()
    assert token == "test_token_abc123"
    assert len(resp_lib.calls) == 1


@resp_lib.activate
def test_token_is_cached() -> None:
    _register_token(3600)
    client = _make_client()
    client._get_token()
    client._get_token()   # second call — should NOT hit the endpoint
    assert len(resp_lib.calls) == 1


@resp_lib.activate
def test_token_is_refreshed_when_near_expiry() -> None:
    # Register two token responses
    _register_token(0)    # first: already-expired immediately
    _register_token(3600) # second: valid
    client = _make_client()
    client._get_token()   # fetches first token (expires_in=0)
    # Manually expire it
    client._token.expires_at = time.time() - 1
    client._get_token()   # should fetch again
    assert len(resp_lib.calls) == 2


@resp_lib.activate
def test_token_fetch_failure_raises() -> None:
    resp_lib.add(resp_lib.POST, TOKEN_URI, status=401)
    client = _make_client()
    with pytest.raises(Exception):
        client._get_token()


# ── Namespace tests ───────────────────────────────────────────────────────────

@resp_lib.activate
def test_list_namespaces_returns_parsed_list() -> None:
    _register_token()
    resp_lib.add(
        resp_lib.GET,
        f"{REST_URI}/v1/{CATALOG_LOWER}/namespaces",
        json={"namespaces": [["finops"], ["subscriber"], ["billing"]]},
        status=200,
    )
    client = _make_client()
    ns_list = client.list_namespaces()
    assert len(ns_list) == 3
    names = {ns.name for ns in ns_list}
    assert names == {"finops", "subscriber", "billing"}


@resp_lib.activate
def test_list_namespaces_empty_catalog() -> None:
    _register_token()
    resp_lib.add(
        resp_lib.GET,
        f"{REST_URI}/v1/{CATALOG_LOWER}/namespaces",
        json={"namespaces": []},
        status=200,
    )
    client = _make_client()
    assert client.list_namespaces() == []


# ── Table tests ───────────────────────────────────────────────────────────────

SAMPLE_METADATA = {
    "metadata-location": "s3://iceberg-lakehouse/iceberg/iceberg_lakehouse/finops/workspace_dbu_daily/metadata/00001-abc.metadata.json",
    "metadata": {
        "location":            "s3://iceberg-lakehouse/iceberg/iceberg_lakehouse/finops/workspace_dbu_daily",
        "current-schema-id":   0,
        "schemas": [{
            "schema-id": 0,
            "type":      "struct",
            "fields": [
                {"id": 1, "name": "workspace_id", "type": "string",  "required": True,  "doc": "Databricks workspace identifier"},
                {"id": 2, "name": "sku",           "type": "string",  "required": True},
                {"id": 3, "name": "usage_date",    "type": "date",    "required": True},
                {"id": 4, "name": "dbus",          "type": "double",  "required": True},
                {"id": 5, "name": "tags",          "type": "string",  "required": False},
            ],
        }],
    },
}


@resp_lib.activate
def test_load_table_parses_schema() -> None:
    _register_token()
    resp_lib.add(
        resp_lib.GET,
        f"{REST_URI}/v1/{CATALOG_LOWER}/namespaces/finops/tables/workspace_dbu_daily",
        json=SAMPLE_METADATA,
        status=200,
    )
    client = _make_client()
    table_meta = client.load_table("finops", "workspace_dbu_daily")

    assert isinstance(table_meta, IcebergTableSummary)
    assert table_meta.namespace == "finops"
    assert table_meta.name == "workspace_dbu_daily"
    assert table_meta.current_schema is not None
    assert len(table_meta.current_schema.fields) == 5

    workspace_field = next(f for f in table_meta.current_schema.fields if f.name == "workspace_id")
    assert workspace_field.type == "string"
    assert workspace_field.required is True
    assert workspace_field.doc == "Databricks workspace identifier"


@resp_lib.activate
def test_load_table_404_raises() -> None:
    _register_token()
    resp_lib.add(
        resp_lib.GET,
        f"{REST_URI}/v1/{CATALOG_LOWER}/namespaces/finops/tables/nonexistent",
        json={"error": {"message": "Table not found"}},
        status=404,
    )
    client = _make_client()
    with pytest.raises(Exception):
        client.load_table("finops", "nonexistent")


@resp_lib.activate
def test_list_tables_returns_names() -> None:
    _register_token()
    resp_lib.add(
        resp_lib.GET,
        f"{REST_URI}/v1/{CATALOG_LOWER}/namespaces/finops/tables",
        json={"identifiers": [
            {"namespace": ["finops"], "name": "workspace_dbu_daily"},
            {"namespace": ["finops"], "name": "sql_warehouse_spend"},
        ]},
        status=200,
    )
    client = _make_client()
    tables = client.list_tables("finops")
    assert set(tables) == {"workspace_dbu_daily", "sql_warehouse_spend"}
