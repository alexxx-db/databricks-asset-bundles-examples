"""conftest.py — shared pytest fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _no_real_aws_calls(monkeypatch):
    """
    Guard: ensure tests that don't use @mock_aws can't accidentally make
    real S3 calls (moto raises if AWS_DEFAULT_REGION isn't set, which is
    a useful safety net, but this fixture makes the intent explicit).
    """
    monkeypatch.setenv("AWS_DEFAULT_REGION",         "us-west-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID",          "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY",      "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN",         "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN",          "testing")
