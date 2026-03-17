"""
schema_sync.py
==============
Schema drift detection and reconciliation between Unity Catalog (Databricks)
and Snowflake Open Catalog (Polaris).

WHY this matters:
  Iceberg tables are written by one system and read by the other.  If a
  Databricks job evolves a table's schema (adds columns, changes nullability,
  renames) and Polaris is not notified, Snowflake queries will fail or silently
  return wrong results.  This module:
    1. Compares the schema as known by UC with the schema registered in Polaris
    2. Classifies differences as COMPATIBLE (safe) vs INCOMPATIBLE (breaking)
    3. Can apply compatible changes to Polaris via the REST API

Iceberg schema evolution rules (safe operations):
  - Add optional columns
  - Widen numeric types (int → long, float → double)
  - Add/update column docs
  - Rename columns (if using field IDs correctly)
NOT safe:
  - Remove required columns
  - Narrow types (long → int)
  - Change column IDs
  - Change partition spec without table rewrite
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from databricks.sdk import WorkspaceClient
from iceberg_catalog.polaris_client import PolarisClient, IcebergField, IcebergSchema

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────────

class DriftKind(str, Enum):
    COLUMN_ADDED_IN_DATABRICKS   = "COLUMN_ADDED_IN_DATABRICKS"
    COLUMN_ADDED_IN_POLARIS      = "COLUMN_ADDED_IN_POLARIS"
    COLUMN_MISSING_IN_POLARIS    = "COLUMN_MISSING_IN_POLARIS"
    COLUMN_MISSING_IN_DATABRICKS = "COLUMN_MISSING_IN_DATABRICKS"
    TYPE_MISMATCH                = "TYPE_MISMATCH"
    NULLABILITY_MISMATCH         = "NULLABILITY_MISMATCH"
    DOC_MISMATCH                 = "DOC_MISMATCH"
    NO_DRIFT                     = "NO_DRIFT"


@dataclass
class ColumnDrift:
    column_name:  str
    kind:         DriftKind
    uc_value:     Optional[str] = None    # type/nullability as seen in UC
    polaris_value: Optional[str] = None   # type/nullability as seen in Polaris
    is_breaking:  bool = False


@dataclass
class SchemaDrift:
    catalog:    str
    schema:     str
    table:      str
    drifts:     list[ColumnDrift] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return bool(self.drifts)

    @property
    def has_breaking_drift(self) -> bool:
        return any(d.is_breaking for d in self.drifts)

    def summary(self) -> str:
        if not self.has_drift:
            return f"{self.catalog}.{self.schema}.{self.table}: no drift"
        lines = [f"{self.catalog}.{self.schema}.{self.table}: {len(self.drifts)} drift(s)"]
        for d in self.drifts:
            breaking = " [BREAKING]" if d.is_breaking else ""
            lines.append(f"  {d.kind.value}: {d.column_name}{breaking}")
            if d.uc_value:
                lines.append(f"    UC:     {d.uc_value}")
            if d.polaris_value:
                lines.append(f"    Polaris:{d.polaris_value}")
        return "\n".join(lines)


# ── Type mapping ──────────────────────────────────────────────────────────────
# UC reports Spark types; Polaris reports Iceberg types.
# This map normalizes both to a canonical form for comparison.
#
# Iceberg → canonical
_ICEBERG_CANONICAL: dict[str, str] = {
    "boolean":        "boolean",
    "int":            "int",
    "long":           "long",
    "float":          "float",
    "double":         "double",
    "decimal":        "decimal",
    "date":           "date",
    "time":           "time",
    "timestamp":      "timestamp",
    "timestamptz":    "timestamptz",
    "string":         "string",
    "uuid":           "uuid",
    "fixed":          "fixed",
    "binary":         "binary",
    "struct":         "struct",
    "list":           "list",
    "map":            "map",
}

# Spark SQL type string → Iceberg canonical
_SPARK_TO_ICEBERG: dict[str, str] = {
    "boolean":        "boolean",
    "byte":           "int",
    "short":          "int",
    "integer":        "int",
    "int":            "int",
    "long":           "long",
    "bigint":         "long",
    "float":          "float",
    "double":         "double",
    "string":         "string",
    "date":           "date",
    "timestamp":      "timestamp",
    "timestamp_ntz":  "timestamp",
    "binary":         "binary",
    "array":          "list",
    "map":            "map",
    "struct":         "struct",
}


def _normalize_type(raw: str) -> str:
    lower = raw.lower().split("(")[0].strip()   # strip precision/scale
    return _SPARK_TO_ICEBERG.get(lower, _ICEBERG_CANONICAL.get(lower, lower))


def _is_safe_widening(uc_type: str, polaris_type: str) -> bool:
    """Return True if going from polaris_type to uc_type is a safe widening."""
    widenings = {("int", "long"), ("float", "double")}
    return (polaris_type, uc_type) in widenings


# ── Schema sync engine ────────────────────────────────────────────────────────

class IcebergSchemaSync:
    """
    Compares and reconciles schemas between Unity Catalog and Polaris.

    Usage::

        sync = IcebergSchemaSync(polaris_client, databricks_workspace_client)
        drift = sync.detect_drift("iceberg_sf", "finops", "workspace_dbu_daily")
        print(drift.summary())
        if not drift.has_breaking_drift:
            sync.apply_compatible_changes(drift)
    """

    def __init__(
        self,
        polaris:     PolarisClient,
        uc_client:   WorkspaceClient,
    ) -> None:
        self._polaris = polaris
        self._uc      = uc_client

    # ── UC schema extraction ──────────────────────────────────────────────────

    def _get_uc_columns(self, catalog: str, schema: str, table: str) -> dict[str, IcebergField]:
        """
        Pull column metadata from UC's table API.
        Returns dict[column_name → IcebergField] for comparison.
        """
        fqn = f"{catalog}.{schema}.{table}"
        try:
            t = self._uc.tables.get(fqn)
        except Exception as e:
            raise ValueError(f"UC table not found: {fqn}") from e

        result: dict[str, IcebergField] = {}
        for i, col in enumerate(t.columns or []):
            result[col.name] = IcebergField(
                field_id = i,                     # UC doesn't expose Iceberg field IDs
                name     = col.name,
                type     = _normalize_type(col.type_text or col.type_name.value),
                required = not col.nullable,
                doc      = col.comment,
            )
        return result

    # ── Polaris schema extraction ─────────────────────────────────────────────

    def _get_polaris_columns(self, namespace: str, table: str) -> dict[str, IcebergField]:
        """Pull column metadata from Polaris and return dict[column_name → IcebergField]."""
        try:
            meta = self._polaris.load_table(namespace, table)
        except Exception as e:
            raise ValueError(f"Polaris table not found: {namespace}.{table}") from e

        if not meta.current_schema:
            return {}
        return {f.name: f for f in meta.current_schema.fields}

    # ── Drift detection ───────────────────────────────────────────────────────

    def detect_drift(
        self,
        uc_catalog:  str,
        uc_schema:   str,
        table:       str,
        namespace:   Optional[str] = None,   # Polaris namespace; defaults to uc_schema
    ) -> SchemaDrift:
        polaris_ns = namespace or uc_schema
        uc_cols     = self._get_uc_columns(uc_catalog, uc_schema, table)
        polaris_cols = self._get_polaris_columns(polaris_ns, table)

        drifts: list[ColumnDrift] = []

        # Columns in UC but not in Polaris
        for name, uc_field in uc_cols.items():
            if name not in polaris_cols:
                drifts.append(ColumnDrift(
                    column_name  = name,
                    kind         = DriftKind.COLUMN_ADDED_IN_DATABRICKS,
                    uc_value     = f"{uc_field.type} required={uc_field.required}",
                    is_breaking  = False,     # adding a column to Polaris is safe
                ))
                continue

            p_field = polaris_cols[name]
            uc_type = _normalize_type(uc_field.type)
            p_type  = _normalize_type(p_field.type)

            # Type mismatch
            if uc_type != p_type:
                breaking = not _is_safe_widening(uc_type, p_type)
                drifts.append(ColumnDrift(
                    column_name   = name,
                    kind          = DriftKind.TYPE_MISMATCH,
                    uc_value      = uc_type,
                    polaris_value = p_type,
                    is_breaking   = breaking,
                ))

            # Nullability: UC optional + Polaris required = breaking (downstream relied on NOT NULL).
            # UC required + Polaris optional = non-breaking (tightening constraint is safe for reads).
            elif uc_field.required != p_field.required:
                breaking = (not uc_field.required) and p_field.required
                drifts.append(ColumnDrift(
                    column_name   = name,
                    kind          = DriftKind.NULLABILITY_MISMATCH,
                    uc_value      = f"required={uc_field.required}",
                    polaris_value = f"required={p_field.required}",
                    is_breaking   = breaking,
                ))

            # Doc drift (never breaking)
            elif uc_field.doc != p_field.doc and (uc_field.doc or p_field.doc):
                drifts.append(ColumnDrift(
                    column_name   = name,
                    kind          = DriftKind.DOC_MISMATCH,
                    uc_value      = uc_field.doc,
                    polaris_value = p_field.doc,
                    is_breaking   = False,
                ))

        # Columns in Polaris but not in UC
        for name in polaris_cols:
            if name not in uc_cols:
                drifts.append(ColumnDrift(
                    column_name   = name,
                    kind          = DriftKind.COLUMN_MISSING_IN_DATABRICKS,
                    polaris_value = f"{polaris_cols[name].type}",
                    is_breaking   = False,
                ))

        result = SchemaDrift(catalog=uc_catalog, schema=uc_schema, table=table, drifts=drifts)
        logger.info(result.summary())
        return result

    def scan_all_tables(self, uc_catalog: str) -> list[SchemaDrift]:
        """Scan every table in every schema of uc_catalog and return drift reports."""
        results: list[SchemaDrift] = []
        namespaces = self._polaris.list_namespaces()

        for ns in namespaces:
            tables = self._polaris.list_tables(ns.name)
            for tbl in tables:
                try:
                    drift = self.detect_drift(uc_catalog, ns.name, tbl)
                    results.append(drift)
                except Exception as e:
                    logger.warning("Could not check %s.%s: %s", ns.name, tbl, e)
        return results

    # ── Apply compatible changes ──────────────────────────────────────────────

    def apply_compatible_changes(self, drift: SchemaDrift) -> None:
        """
        Push UC schema additions and doc updates to Polaris via the table
        update API.  ONLY applies non-breaking changes.  Raises if breaking
        drift is detected.
        """
        if drift.has_breaking_drift:
            breaking = [d for d in drift.drifts if d.is_breaking]
            raise ValueError(
                f"Cannot auto-apply breaking schema changes for "
                f"{drift.catalog}.{drift.schema}.{drift.table}: "
                + ", ".join(f"{d.kind.value}:{d.column_name}" for d in breaking)
            )

        if not drift.has_drift:
            logger.info("No changes to apply for %s.%s.%s", drift.catalog, drift.schema, drift.table)
            return

        # Reload current Polaris schema to get field IDs
        polaris_meta = self._polaris.load_table(drift.schema, drift.table)
        if not polaris_meta.current_schema:
            logger.warning("No current schema in Polaris for %s.%s — skipping update", drift.schema, drift.table)
            return

        existing_fields = {f.name: f for f in polaris_meta.current_schema.fields}
        max_field_id    = max((f.field_id for f in polaris_meta.current_schema.fields), default=0)

        # Build an Iceberg UpdateSchema request
        # Polaris supports the standard Iceberg CommitTableRequest with updates
        updates: list[dict] = []

        uc_cols = self._get_uc_columns(drift.catalog, drift.schema, drift.table)

        for d in drift.drifts:
            if d.kind == DriftKind.COLUMN_ADDED_IN_DATABRICKS:
                uc_field = uc_cols[d.column_name]
                max_field_id += 1
                updates.append({
                    "action":   "add-column",
                    "name":     d.column_name,
                    "type":     uc_field.type,
                    "required": uc_field.required,
                    "doc":      uc_field.doc,
                    "field-id": max_field_id,
                })
            elif d.kind == DriftKind.DOC_MISMATCH and uc_cols.get(d.column_name):
                existing = existing_fields.get(d.column_name)
                if existing:
                    updates.append({
                        "action":  "update-column",
                        "name":    d.column_name,
                        "doc":     uc_cols[d.column_name].doc or "",
                    })

        if not updates:
            logger.info("No applicable updates to commit for %s.%s.%s", drift.catalog, drift.schema, drift.table)
            return

        # Commit the schema update via the Iceberg REST update endpoint
        commit_body = {
            "identifier": {
                "namespace": [drift.schema],
                "name":      drift.table,
            },
            "requirements": [
                {
                    "type":              "assert-current-schema-id",
                    "current-schema-id": polaris_meta.current_schema.schema_id,
                }
            ],
            "updates": [{"action": "set-schema", "schema": self._build_updated_schema(
                polaris_meta.current_schema, updates
            )}],
        }

        try:
            self._polaris._post(
                f"/namespaces/{drift.schema}/tables/{drift.table}",
                commit_body,
            )
            logger.info(
                "Applied %d schema update(s) to Polaris for %s.%s",
                len(updates), drift.schema, drift.table
            )
        except Exception as e:
            logger.error("Failed to apply schema update: %s", e)
            raise

    def _build_updated_schema(self, base: IcebergSchema, updates: list[dict]) -> dict:
        """Merge updates into a Polaris-ready schema dict."""
        fields = [
            {
                "id":       f.field_id,
                "name":     f.name,
                "type":     f.type,
                "required": f.required,
                "doc":      f.doc,
            }
            for f in base.fields
        ]
        doc_updates = {u["name"]: u["doc"] for u in updates if u["action"] == "update-column"}
        for f in fields:
            if f["name"] in doc_updates:
                f["doc"] = doc_updates[f["name"]]

        for u in updates:
            if u["action"] == "add-column":
                fields.append({
                    "id":       u["field-id"],
                    "name":     u["name"],
                    "type":     u["type"],
                    "required": u["required"],
                    "doc":      u.get("doc"),
                })

        return {
            "type":      "struct",
            "schema-id": base.schema_id + 1,
            "fields":    fields,
        }
