# conftest.py is used to configure pytest.
# This file is in the root since it affects all tests through this bundle.
# It makes sure all 'assets/*' directories are added to `sys.path` so that
# tests can import them.
# dlt/spark setup is optional so unit tests (e.g. add_asset) can run without heavy deps.
import os
import pathlib
import sys

import pytest

# Dynamically find and add all `assets/*` directories to `sys.path`
_assets_dir = pathlib.Path(__file__).parent / "assets"
if _assets_dir.exists():
    for path in _assets_dir.glob("*"):
        resolved_path = str(path.resolve())
        if resolved_path not in sys.path:
            sys.path.append(resolved_path)

try:
    import warnings

    import dlt
    from databricks.connect import DatabricksSession
    from pyspark.sql import SparkSession

    # For older databricks-connect, work around issues importing SparkSession
    # and errors when SPARK_REMOTE is set.
    SparkSession.builder = DatabricksSession.builder
    os.environ.pop("SPARK_REMOTE", None)

    # Make dlt.views in 'sources/dev' available for tests
    warnings.filterwarnings(
        "ignore",
        message="This is a stub that only contains the interfaces to Delta Live Tables.*",
        category=UserWarning,
    )
    dlt.enable_local_execution()
    dlt.view = lambda func=None, *args, **kwargs: func or (lambda f: f)

    _HAS_DLT = True
except ImportError:
    _HAS_DLT = False


# Provide a 'spark' fixture for tests that need it (only when dlt/connect available).
# autouse only when dlt is available so unit tests (e.g. add_asset) run without heavy deps.
@pytest.fixture(scope="session", autouse=_HAS_DLT)
def spark():
    if not _HAS_DLT:
        pytest.skip("dlt/databricks-connect not installed; skipping spark fixture")
    from databricks.connect import DatabricksSession

    if hasattr(DatabricksSession.builder, "validateSession"):
        return DatabricksSession.builder.validateSession().getOrCreate()
    return DatabricksSession.builder.getOrCreate()
