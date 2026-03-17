"""Tests for add_asset.py (argument parsing and no shell injection)."""

import sys
from pathlib import Path
from unittest.mock import patch

# Add scripts dir so we can import add_asset
_scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_scripts_dir))

import add_asset  # noqa: E402


class TestParsePassthroughArgs:
    def test_empty(self):
        assert add_asset._parse_passthrough_args([]) == []

    def test_allowlisted_options_with_values(self):
        assert add_asset._parse_passthrough_args(["--target", "dev"]) == ["--target", "dev"]
        assert add_asset._parse_passthrough_args(["--config", "bundle.yml"]) == [
            "--config",
            "bundle.yml",
        ]

    def test_unknown_options_ignored(self):
        # Malicious or unknown args must not appear in output
        assert add_asset._parse_passthrough_args([";", "rm", "-rf", "/"]) == []
        assert add_asset._parse_passthrough_args(["$(whoami)"]) == []
        assert add_asset._parse_passthrough_args(["`id`"]) == []

    def test_mixed(self):
        result = add_asset._parse_passthrough_args(
            ["--target", "prod", "evil; rm -rf /", "--config", "other.yml"]
        )
        assert result == ["--target", "prod", "--config", "other.yml"]


class TestInitBundle:
    def test_calls_subprocess_with_list_and_shell_false(self):
        with patch("add_asset.subprocess.run") as run:
            with patch("add_asset.shutil.which", return_value="/usr/bin/databricks"):
                with patch.object(sys, "argv", ["add_asset.py", "etl-pipeline"]):
                    add_asset.init_bundle("etl-pipeline")
        run.assert_called_once()
        args = run.call_args
        assert args[1].get("shell") is False
        cmd = args[0][0]
        assert isinstance(cmd, list)
        assert cmd[0] == "/usr/bin/databricks"
        assert "bundle" in cmd
        assert "init" in cmd
        assert "etl-pipeline" in "".join(cmd)
