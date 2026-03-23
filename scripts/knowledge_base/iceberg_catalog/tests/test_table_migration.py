"""
tests/test_table_migration.py
=============================
Tests for IcebergTableRegistrar metadata path resolution.
Uses moto to mock S3 — no real AWS calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from iceberg_catalog.table_migration import IcebergTableRegistrar

BUCKET = "iceberg-lakehouse"
PREFIX = "iceberg/iceberg_db/finops/pipeline_runs"


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _metadata_json(snapshot_id: int = 1001, schema_id: int = 0) -> dict:
    return {
        "format-version":       2,
        "table-uuid":           "aaaabbbb-cccc-dddd-eeee-ffffffffffff",
        "location":             f"s3://{BUCKET}/{PREFIX}",
        "current-schema-id":    schema_id,
        "current-snapshot-id":  snapshot_id,
        "schemas": [{"schema-id": 0, "type": "struct", "fields": []}],
        "snapshots": [{"snapshot-id": snapshot_id, "timestamp-ms": 1700000000000}],
    }


def _make_registrar(uc_client=None) -> IcebergTableRegistrar:
    return IcebergTableRegistrar(
        uc_client          = uc_client or MagicMock(),
        sf_account         = "example.us-west-2.aws",
        sf_user            = "test_user",
        sf_password        = "test_password",
        sf_warehouse       = "COMPUTE_WH",
        sf_polaris_catalog = "ICEBERG_LAKEHOUSE",
    )


# ── S3 metadata resolution ────────────────────────────────────────────────────

@mock_aws
def test_resolve_metadata_via_version_hint():
    """version-hint.text present → resolves to the correct versioned file."""
    s3 = boto3.client("s3", region_name="us-west-2")
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "us-west-2"})

    meta_prefix = f"{PREFIX}/metadata"
    meta_key    = f"{meta_prefix}/00001-abc123.metadata.json"
    hint_key    = f"{meta_prefix}/version-hint.text"

    s3.put_object(Bucket=BUCKET, Key=hint_key,  Body=b"1")
    s3.put_object(Bucket=BUCKET, Key=meta_key,  Body=json.dumps(_metadata_json()).encode())

    reg = _make_registrar()
    resolved = reg._resolve_current_metadata(BUCKET, PREFIX)
    assert resolved == meta_key


@mock_aws
def test_resolve_metadata_fallback_to_lexicographic_latest():
    """No version-hint.text → falls back to lexicographically latest .metadata.json."""
    s3 = boto3.client("s3", region_name="us-west-2")
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "us-west-2"})

    meta_prefix = f"{PREFIX}/metadata"
    old_key     = f"{meta_prefix}/00001-aaa.metadata.json"
    new_key     = f"{meta_prefix}/00002-bbb.metadata.json"

    s3.put_object(Bucket=BUCKET, Key=old_key, Body=json.dumps(_metadata_json(1001)).encode())
    s3.put_object(Bucket=BUCKET, Key=new_key, Body=json.dumps(_metadata_json(1002)).encode())

    reg = _make_registrar()
    resolved = reg._resolve_current_metadata(BUCKET, PREFIX)
    # lexicographic sort: 00002 > 00001
    assert resolved == new_key


@mock_aws
def test_resolve_metadata_raises_when_no_files():
    s3 = boto3.client("s3", region_name="us-west-2")
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "us-west-2"})

    reg = _make_registrar()
    with pytest.raises(FileNotFoundError, match=r"No .metadata.json files"):
        reg._resolve_current_metadata(BUCKET, PREFIX)


@mock_aws
def test_read_metadata_snapshot_parses_ids():
    s3 = boto3.client("s3", region_name="us-west-2")
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "us-west-2"})

    meta_key = f"{PREFIX}/metadata/00001-abc.metadata.json"
    s3.put_object(Bucket=BUCKET, Key=meta_key, Body=json.dumps(_metadata_json(snapshot_id=9999, schema_id=2)).encode())

    reg = _make_registrar()
    snapshot_id, schema_id = reg._read_metadata_snapshot(BUCKET, meta_key)
    assert snapshot_id == 9999
    assert schema_id   == 2


# ── get_table_location ────────────────────────────────────────────────────────

@mock_aws
def test_get_table_location_resolves_full_path():
    s3 = boto3.client("s3", region_name="us-west-2")
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "us-west-2"})

    meta_key = f"{PREFIX}/metadata/00001-abc.metadata.json"
    s3.put_object(Bucket=BUCKET, Key=meta_key, Body=json.dumps(_metadata_json(1234, 0)).encode())

    uc = MagicMock()
    uc_table = MagicMock()
    uc_table.storage_location = f"s3://{BUCKET}/{PREFIX}"
    uc.tables.get.return_value = uc_table

    reg = _make_registrar(uc)
    loc = reg.get_table_location("iceberg_db", "finops", "pipeline_runs")

    assert loc.catalog           == "iceberg_db"
    assert loc.schema            == "finops"
    assert loc.table             == "pipeline_runs"
    assert loc.s3_base_location  == f"s3://{BUCKET}/{PREFIX}"
    assert loc.metadata_location == f"s3://{BUCKET}/{meta_key}"
    assert loc.snapshot_id       == 1234
    assert loc.schema_id         == 0


def test_get_table_location_raises_when_no_storage_location():
    uc = MagicMock()
    uc_table = MagicMock()
    uc_table.storage_location = None
    uc.tables.get.return_value = uc_table

    reg = _make_registrar(uc)
    with pytest.raises(ValueError, match="no storage_location"):
        reg.get_table_location("iceberg_db", "finops", "some_table")
