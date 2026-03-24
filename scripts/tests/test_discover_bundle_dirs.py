"""Tests for discover_bundle_dirs.py."""

import sys
from pathlib import Path

# Add scripts directory to sys.path so we can import the module
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from discover_bundle_dirs import _iter_bundle_ymls, discover_bundle_dirs, validate_bundle_schemas  # noqa: E402


def _write_yml(path: Path, content: str) -> None:
    """Helper to write a databricks.yml file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestDiscoverBundleDirs:
    """Tests for discover_bundle_dirs()."""

    def test_finds_valid_bundles(self, tmp_path):
        _write_yml(tmp_path / "project_a" / "databricks.yml", "bundle:\n  name: project_a\n")
        _write_yml(tmp_path / "project_b" / "databricks.yml", "bundle:\n  name: project_b\n")
        result = discover_bundle_dirs(tmp_path)
        assert result == ["project_a", "project_b"]

    def test_skips_contrib_templates(self, tmp_path):
        _write_yml(tmp_path / "valid" / "databricks.yml", "bundle:\n  name: valid\n")
        _write_yml(tmp_path / "contrib" / "templates" / "thing" / "databricks.yml", "bundle:\n  name: skip_me\n")
        result = discover_bundle_dirs(tmp_path)
        assert result == ["valid"]

    def test_skips_missing_bundle_name(self, tmp_path):
        _write_yml(tmp_path / "no_name" / "databricks.yml", "bundle:\n  foo: bar\n")
        result = discover_bundle_dirs(tmp_path)
        assert result == []

    def test_skips_non_dict_bundle(self, tmp_path):
        _write_yml(tmp_path / "bad" / "databricks.yml", "bundle: just_a_string\n")
        result = discover_bundle_dirs(tmp_path)
        assert result == []

    def test_empty_dir(self, tmp_path):
        result = discover_bundle_dirs(tmp_path)
        assert result == []

    def test_malformed_yaml(self, tmp_path):
        _write_yml(tmp_path / "bad_yaml" / "databricks.yml", "{{invalid: yaml: [[[")
        result = discover_bundle_dirs(tmp_path)
        assert result == []

    def test_nested_bundle(self, tmp_path):
        _write_yml(tmp_path / "parent" / "child" / "databricks.yml", "bundle:\n  name: nested\n")
        result = discover_bundle_dirs(tmp_path)
        assert result == ["parent/child"]

    def test_deduplicates(self, tmp_path):
        # Same directory shouldn't appear twice (only one databricks.yml per dir anyway)
        _write_yml(tmp_path / "proj" / "databricks.yml", "bundle:\n  name: proj\n")
        result = discover_bundle_dirs(tmp_path)
        assert result == ["proj"]


class TestValidateBundleSchemas:
    """Tests for validate_bundle_schemas()."""

    def test_valid_bundles_returns_true(self, tmp_path):
        _write_yml(tmp_path / "a" / "databricks.yml", "bundle:\n  name: a\n")
        _write_yml(tmp_path / "b" / "databricks.yml", "bundle:\n  name: b\n")
        assert validate_bundle_schemas(tmp_path, quiet=True) is True

    def test_missing_bundle_name_returns_false(self, tmp_path):
        _write_yml(tmp_path / "bad" / "databricks.yml", "bundle:\n  foo: bar\n")
        assert validate_bundle_schemas(tmp_path, quiet=True) is False

    def test_malformed_yaml_returns_false(self, tmp_path):
        _write_yml(tmp_path / "bad" / "databricks.yml", "{{not: valid: yaml[[[")
        assert validate_bundle_schemas(tmp_path, quiet=True) is False

    def test_non_mapping_returns_false(self, tmp_path):
        _write_yml(tmp_path / "list" / "databricks.yml", "- item1\n- item2\n")
        assert validate_bundle_schemas(tmp_path, quiet=True) is False

    def test_empty_dir_returns_true(self, tmp_path):
        # No bundles found, no errors => checked == 0, still prints summary and returns True
        assert validate_bundle_schemas(tmp_path, quiet=True) is True


class TestIterBundleYmls:
    """Tests for _iter_bundle_ymls()."""

    def test_yields_databricks_ymls(self, tmp_path):
        _write_yml(tmp_path / "a" / "databricks.yml", "content")
        _write_yml(tmp_path / "b" / "databricks.yml", "content")
        results = list(_iter_bundle_ymls(tmp_path))
        assert len(results) == 2
        rel_paths = sorted(str(r[1]) for r in results)
        assert rel_paths == ["a/databricks.yml", "b/databricks.yml"]

    def test_skips_contrib_templates(self, tmp_path):
        _write_yml(tmp_path / "contrib" / "templates" / "x" / "databricks.yml", "content")
        _write_yml(tmp_path / "valid" / "databricks.yml", "content")
        results = list(_iter_bundle_ymls(tmp_path))
        assert len(results) == 1
        assert "valid" in str(results[0][1])

    def test_skips_when_both_contrib_and_templates_in_path(self, tmp_path):
        # Must have BOTH contrib and templates in path parts to be skipped
        _write_yml(tmp_path / "contrib" / "databricks.yml", "content")
        _write_yml(tmp_path / "templates" / "databricks.yml", "content")
        results = list(_iter_bundle_ymls(tmp_path))
        # Both should be included since neither has BOTH contrib AND templates
        assert len(results) == 2
