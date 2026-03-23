"""
tests/test_schema_sync.py
=========================
Unit tests for IcebergSchemaSync drift detection logic.

We mock:
  - WorkspaceClient.tables.get()    — UC column metadata
  - PolarisClient.load_table()      — Polaris schema

We test:
  - No drift when schemas match
  - COLUMN_ADDED_IN_DATABRICKS when UC has a new column
  - TYPE_MISMATCH breaking vs. safe widening
  - NULLABILITY_MISMATCH breaking vs. safe direction
  - DOC_MISMATCH (non-breaking)
  - apply_compatible_changes raises on breaking drift
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from iceberg_catalog.polaris_client import (
    IcebergField,
    IcebergSchema,
    IcebergTableSummary,
    PolarisClient,
)
from iceberg_catalog.schema_sync import DriftKind, IcebergSchemaSync

# ── Helpers ───────────────────────────────────────────────────────────────────

def _polaris_client_mock() -> MagicMock:
    return MagicMock(spec=PolarisClient)


def _uc_client_mock() -> MagicMock:
    return MagicMock()


def _uc_column(name: str, type_text: str, nullable: bool = True, comment: str | None = None):
    col = MagicMock()
    col.name       = name
    col.type_text  = type_text
    col.type_name  = MagicMock()
    col.type_name.value = type_text
    col.nullable   = nullable
    col.comment    = comment
    return col


def _uc_table(columns: list) -> MagicMock:
    t = MagicMock()
    t.columns = columns
    return t


def _polaris_table(fields: list[IcebergField]) -> IcebergTableSummary:
    return IcebergTableSummary(
        namespace         = "finops",
        name              = "workspace_dbu_daily",
        location          = "s3://bucket/finops/workspace_dbu_daily",
        metadata_location = "s3://bucket/finops/workspace_dbu_daily/metadata/00001.metadata.json",
        current_schema    = IcebergSchema(schema_id=0, fields=fields),
    )


# ── No drift ──────────────────────────────────────────────────────────────────

def test_no_drift_when_schemas_match():
    polaris = _polaris_client_mock()
    uc      = _uc_client_mock()

    uc.tables.get.return_value = _uc_table([
        _uc_column("workspace_id", "string",  nullable=False),
        _uc_column("dbus",         "double",  nullable=False),
        _uc_column("usage_date",   "date",    nullable=False),
    ])
    polaris.load_table.return_value = _polaris_table([
        IcebergField(1, "workspace_id", "string",   required=True),
        IcebergField(2, "dbus",         "double",   required=True),
        IcebergField(3, "usage_date",   "date",     required=True),
    ])

    sync  = IcebergSchemaSync(polaris, uc)
    drift = sync.detect_drift("iceberg_sf", "finops", "workspace_dbu_daily")

    assert not drift.has_drift
    assert not drift.has_breaking_drift


# ── Column added in Databricks ────────────────────────────────────────────────

def test_column_added_in_databricks_is_non_breaking():
    polaris = _polaris_client_mock()
    uc      = _uc_client_mock()

    uc.tables.get.return_value = _uc_table([
        _uc_column("workspace_id", "string", nullable=False),
        _uc_column("dbus",         "double", nullable=False),
        _uc_column("new_col",      "string", nullable=True),   # added in UC
    ])
    polaris.load_table.return_value = _polaris_table([
        IcebergField(1, "workspace_id", "string", required=True),
        IcebergField(2, "dbus",         "double", required=True),
    ])

    sync  = IcebergSchemaSync(polaris, uc)
    drift = sync.detect_drift("iceberg_sf", "finops", "workspace_dbu_daily")

    assert drift.has_drift
    assert not drift.has_breaking_drift
    col_drift = next(d for d in drift.drifts if d.column_name == "new_col")
    assert col_drift.kind == DriftKind.COLUMN_ADDED_IN_DATABRICKS
    assert col_drift.is_breaking is False


# ── Type mismatch ─────────────────────────────────────────────────────────────

def test_type_mismatch_widening_is_not_breaking():
    """int in Polaris → long in UC is a safe widening per Iceberg spec."""
    polaris = _polaris_client_mock()
    uc      = _uc_client_mock()

    uc.tables.get.return_value = _uc_table([
        _uc_column("count_col", "long", nullable=False),  # UC: long
    ])
    polaris.load_table.return_value = _polaris_table([
        IcebergField(1, "count_col", "int", required=True),  # Polaris: int
    ])

    sync  = IcebergSchemaSync(polaris, uc)
    drift = sync.detect_drift("iceberg_sf", "finops", "workspace_dbu_daily")

    assert drift.has_drift
    td = next(d for d in drift.drifts if d.kind == DriftKind.TYPE_MISMATCH)
    assert td.is_breaking is False


def test_type_mismatch_narrowing_is_breaking():
    """long in Polaris → int in UC is a breaking narrowing."""
    polaris = _polaris_client_mock()
    uc      = _uc_client_mock()

    uc.tables.get.return_value = _uc_table([
        _uc_column("count_col", "integer", nullable=False),  # UC: int
    ])
    polaris.load_table.return_value = _polaris_table([
        IcebergField(1, "count_col", "long", required=True),  # Polaris: long
    ])

    sync  = IcebergSchemaSync(polaris, uc)
    drift = sync.detect_drift("iceberg_sf", "finops", "workspace_dbu_daily")

    assert drift.has_breaking_drift
    td = next(d for d in drift.drifts if d.kind == DriftKind.TYPE_MISMATCH)
    assert td.is_breaking is True


# ── Nullability mismatch ──────────────────────────────────────────────────────

def test_making_required_column_optional_in_uc_is_breaking():
    """Polaris says required; UC says nullable → breaking (can't enforce NOT NULL anymore)."""
    polaris = _polaris_client_mock()
    uc      = _uc_client_mock()

    uc.tables.get.return_value = _uc_table([
        _uc_column("workspace_id", "string", nullable=True),   # UC: nullable
    ])
    polaris.load_table.return_value = _polaris_table([
        IcebergField(1, "workspace_id", "string", required=True),  # Polaris: required
    ])

    sync  = IcebergSchemaSync(polaris, uc)
    drift = sync.detect_drift("iceberg_sf", "finops", "workspace_dbu_daily")

    assert drift.has_breaking_drift


def test_making_optional_column_required_in_uc_is_not_breaking():
    """Polaris nullable; UC required — technically an assertion, not breaking for reads."""
    polaris = _polaris_client_mock()
    uc      = _uc_client_mock()

    uc.tables.get.return_value = _uc_table([
        _uc_column("workspace_id", "string", nullable=False),
    ])
    polaris.load_table.return_value = _polaris_table([
        IcebergField(1, "workspace_id", "string", required=False),
    ])

    sync  = IcebergSchemaSync(polaris, uc)
    drift = sync.detect_drift("iceberg_sf", "finops", "workspace_dbu_daily")

    # has drift but not breaking
    assert drift.has_drift
    assert not drift.has_breaking_drift


# ── Doc mismatch ──────────────────────────────────────────────────────────────

def test_doc_mismatch_is_non_breaking():
    polaris = _polaris_client_mock()
    uc      = _uc_client_mock()

    uc.tables.get.return_value = _uc_table([
        _uc_column("dbus", "double", nullable=False, comment="Updated description"),
    ])
    polaris.load_table.return_value = _polaris_table([
        IcebergField(1, "dbus", "double", required=True, doc="Old description"),
    ])

    sync  = IcebergSchemaSync(polaris, uc)
    drift = sync.detect_drift("iceberg_sf", "finops", "workspace_dbu_daily")

    assert drift.has_drift
    assert not drift.has_breaking_drift
    d = drift.drifts[0]
    assert d.kind == DriftKind.DOC_MISMATCH
    assert d.is_breaking is False


# ── apply_compatible_changes ──────────────────────────────────────────────────

def test_apply_compatible_changes_raises_on_breaking_drift():
    polaris = _polaris_client_mock()
    uc      = _uc_client_mock()

    # Type narrowing → breaking
    uc.tables.get.return_value = _uc_table([
        _uc_column("count_col", "integer", nullable=False),
    ])
    polaris.load_table.return_value = _polaris_table([
        IcebergField(1, "count_col", "long", required=True),
    ])

    sync  = IcebergSchemaSync(polaris, uc)
    drift = sync.detect_drift("iceberg_sf", "finops", "workspace_dbu_daily")

    with pytest.raises(ValueError, match="breaking"):
        sync.apply_compatible_changes(drift)


def test_apply_compatible_changes_no_op_when_no_drift():
    polaris = _polaris_client_mock()
    uc      = _uc_client_mock()

    uc.tables.get.return_value = _uc_table([
        _uc_column("workspace_id", "string", nullable=False),
    ])
    polaris.load_table.return_value = _polaris_table([
        IcebergField(1, "workspace_id", "string", required=True),
    ])

    sync  = IcebergSchemaSync(polaris, uc)
    drift = sync.detect_drift("iceberg_sf", "finops", "workspace_dbu_daily")

    # Should not call any Polaris write methods
    sync.apply_compatible_changes(drift)
    polaris._post.assert_not_called()
