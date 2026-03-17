"""
polaris_client.py
=================
Typed client for the Snowflake Open Catalog (Apache Polaris) Iceberg REST API.

WHY a custom client rather than using pyiceberg directly:
  - pyiceberg's REST catalog client works, but doesn't expose Polaris-specific
    extensions (catalog roles, principal management, async refresh).
  - We need direct control over auth token refresh and retry semantics.
  - This client is intentionally thin: it maps 1:1 to the Iceberg REST spec
    (https://iceberg.apache.org/rest-api/), with Polaris extensions in a
    separate section at the bottom.

Thread safety: PolarisClient is NOT thread-safe.  Create one per thread/task.
Token caching: tokens are cached in-process and refreshed 60s before expiry.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class IcebergField:
    field_id:  int
    name:      str
    type:      str            # Iceberg type string e.g. "long", "string", "timestamp"
    required:  bool = True
    doc:       Optional[str] = None

@dataclass
class IcebergSchema:
    schema_id: int
    fields:    list[IcebergField] = field(default_factory=list)

@dataclass
class IcebergTableSummary:
    namespace:   str           # dot-separated, e.g. "finops"
    name:        str
    location:    str           # s3://... base location
    metadata_location: str     # s3://.../.../metadata/00001-<uuid>.metadata.json
    current_schema: Optional[IcebergSchema] = None

@dataclass
class PolarisNamespace:
    name:       str            # single-level name
    properties: dict[str, str] = field(default_factory=dict)

@dataclass
class _OAuthToken:
    access_token: str
    expires_at:   float        # Unix timestamp


# ── Client ────────────────────────────────────────────────────────────────────

class PolarisClient:
    """
    Minimal Iceberg REST Catalog client for Snowflake Open Catalog (Polaris).

    Usage::

        client = PolarisClient.from_secrets(
            snowflake_account = "example.us-west-2.aws",
            secret_scope      = "iceberg-polaris",
            principal_role    = "databricks_svc_role",
        )
        namespaces = client.list_namespaces()
        tables = client.list_tables("finops")
        meta = client.load_table("finops", "workspace_dbu_daily")
    """

    def __init__(
        self,
        rest_uri:        str,
        token_endpoint:  str,
        client_id:       str,
        client_secret:   str,
        principal_role:  str,
        catalog_name:    str,
        timeout_seconds: int = 30,
    ) -> None:
        self._rest_uri       = rest_uri.rstrip("/")
        self._token_endpoint = token_endpoint
        self._client_id      = client_id
        self._client_secret  = client_secret
        self._scope          = f"PRINCIPAL_ROLE:{principal_role}"
        self._catalog_name   = catalog_name
        self._timeout        = timeout_seconds
        self._token: Optional[_OAuthToken] = None

        # Retry on transient 5xx and connection errors
        retry = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session = requests.Session()
        self._session.mount("https://", adapter)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_secrets(
        cls,
        snowflake_account: str,
        secret_scope:      str,
        principal_role:    str,
        catalog_name:      str = "ICEBERG_LAKEHOUSE",
    ) -> "PolarisClient":
        """
        Construct from Databricks secrets.  Call from inside a Databricks
        notebook or job task where dbutils is available.
        """
        try:
            from databricks.sdk.runtime import dbutils  # available in runtime
        except ImportError:
            raise RuntimeError(
                "PolarisClient.from_secrets() must be called inside a "
                "Databricks runtime (dbutils not available)"
            )

        account = snowflake_account.rstrip("/")
        return cls(
            rest_uri        = f"https://{account}.snowflakecomputing.com/polaris/api/catalog",
            token_endpoint  = f"https://{account}.snowflakecomputing.com/oauth/token",
            client_id       = dbutils.secrets.get(secret_scope, "polaris_client_id"),
            client_secret   = dbutils.secrets.get(secret_scope, "polaris_client_secret"),
            principal_role  = principal_role,
            catalog_name    = catalog_name,
        )

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _get_token(self) -> str:
        now = time.time()
        if self._token and self._token.expires_at > now + 60:
            return self._token.access_token

        resp = requests.post(
            self._token_endpoint,
            data={
                "grant_type":    "client_credentials",
                "client_id":     self._client_id,
                "client_secret": self._client_secret,
                "scope":         self._scope,
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = _OAuthToken(
            access_token = body["access_token"],
            expires_at   = now + body.get("expires_in", 3600),
        )
        logger.debug("OAuth token refreshed, expires in %ds", body.get("expires_in", 3600))
        return self._token.access_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization":  f"Bearer {self._get_token()}",
            "Content-Type":   "application/json",
            "Accept":         "application/json",
            "X-Iceberg-Access-Delegation": "vended-credentials",
        }

    def _url(self, path: str) -> str:
        # Polaris REST prefix is the catalog name (lowercased)
        return f"{self._rest_uri}/v1/{self._catalog_name.lower()}{path}"

    def _get(self, path: str) -> Any:
        resp = self._session.get(self._url(path), headers=self._headers(), timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> Any:
        resp = self._session.post(
            self._url(path), headers=self._headers(), json=body, timeout=self._timeout
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def _delete(self, path: str) -> None:
        resp = self._session.delete(self._url(path), headers=self._headers(), timeout=self._timeout)
        resp.raise_for_status()

    # ── Namespace (schema) operations ─────────────────────────────────────────

    def list_namespaces(self, parent: Optional[str] = None) -> list[PolarisNamespace]:
        """List all namespaces (schemas) in the catalog."""
        params = f"?parent={parent}" if parent else ""
        body = self._get(f"/namespaces{params}")
        results = []
        for ns_entry in body.get("namespaces", []):
            # ns_entry is a list like ["finops"] for a single-level namespace
            name = ".".join(ns_entry) if isinstance(ns_entry, list) else ns_entry
            results.append(PolarisNamespace(name=name))
        return results

    def create_namespace(self, name: str, properties: Optional[dict[str, str]] = None) -> PolarisNamespace:
        body = self._post("/namespaces", {
            "namespace":  [name],
            "properties": properties or {},
        })
        return PolarisNamespace(name=name, properties=body.get("properties", {}))

    def drop_namespace(self, name: str) -> None:
        self._delete(f"/namespaces/{name}")

    # ── Table operations ──────────────────────────────────────────────────────

    def list_tables(self, namespace: str) -> list[str]:
        """Return table names in the given namespace."""
        body = self._get(f"/namespaces/{namespace}/tables")
        return [t["name"] if isinstance(t, dict) else t for t in body.get("identifiers", [])]

    def load_table(self, namespace: str, table: str) -> IcebergTableSummary:
        """Load table metadata — returns schema, location, and current metadata pointer."""
        body = self._get(f"/namespaces/{namespace}/tables/{table}")
        meta = body.get("metadata", {})

        # Parse current schema
        current_schema_id = meta.get("current-schema-id", 0)
        schemas_raw = meta.get("schemas", [])
        current_schema = None
        for s in schemas_raw:
            if s.get("schema-id") == current_schema_id:
                current_schema = IcebergSchema(
                    schema_id = current_schema_id,
                    fields = [
                        IcebergField(
                            field_id = f["id"],
                            name     = f["name"],
                            type     = f["type"] if isinstance(f["type"], str) else str(f["type"]),
                            required = f.get("required", True),
                            doc      = f.get("doc"),
                        )
                        for f in s.get("fields", [])
                    ],
                )
                break

        return IcebergTableSummary(
            namespace          = namespace,
            name               = table,
            location           = meta.get("location", ""),
            metadata_location  = body.get("metadata-location", ""),
            current_schema     = current_schema,
        )

    def create_table(
        self,
        namespace:       str,
        table:           str,
        schema:          dict,                    # Iceberg schema dict
        location:        Optional[str] = None,
        partition_spec:  Optional[dict] = None,
        properties:      Optional[dict] = None,
    ) -> IcebergTableSummary:
        """
        Create a new Iceberg table in Polaris.
        schema must be an Iceberg schema dict:
          {"type": "struct", "fields": [{"id": 1, "name": "col", "type": "string", "required": True}]}
        """
        body: dict[str, Any] = {
            "name":   table,
            "schema": schema,
        }
        if location:
            body["location"] = location
        if partition_spec:
            body["partition-spec"] = partition_spec
        if properties:
            body["properties"] = properties

        resp = self._post(f"/namespaces/{namespace}/tables", body)
        return self.load_table(namespace, table)

    def drop_table(self, namespace: str, table: str, purge: bool = False) -> None:
        suffix = "?purgeRequested=true" if purge else ""
        self._delete(f"/namespaces/{namespace}/tables/{table}{suffix}")

    # ── Polaris-specific: catalog config ─────────────────────────────────────

    def get_config(self) -> dict:
        """
        GET /v1/config — returns catalog-level properties including the
        S3 storage root and any credential vending config.
        """
        resp = self._session.get(
            f"{self._rest_uri}/v1/config",
            headers=self._headers(),
            timeout=self._timeout,
            params={"warehouse": self._catalog_name},
        )
        resp.raise_for_status()
        return resp.json()
