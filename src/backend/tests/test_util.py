"""Tests for util: file-backed secret resolution."""

from bark_backend.util import resolve_env_secret


class TestResolveEnvSecret:
    def test_plain_value(self, monkeypatch):
        monkeypatch.setenv("TEST_SECRET", "plain-value")
        assert resolve_env_secret("TEST_SECRET") == "plain-value"

    def test_file_prefix_reads_file(self, monkeypatch, tmp_path):
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("from-file\n")
        monkeypatch.setenv("TEST_SECRET", f"file:{secret_file}")
        assert resolve_env_secret("TEST_SECRET") == "from-file"

    def test_file_missing_returns_none(self, monkeypatch):
        monkeypatch.setenv("TEST_SECRET", "file:/no/such/file")
        assert resolve_env_secret("TEST_SECRET") is None

    def test_unset_returns_none(self, monkeypatch):
        monkeypatch.delenv("TEST_SECRET", raising=False)
        assert resolve_env_secret("TEST_SECRET") is None

    def test_unset_returns_default(self, monkeypatch):
        monkeypatch.delenv("TEST_SECRET", raising=False)
        assert resolve_env_secret("TEST_SECRET", "fallback") == "fallback"

    def test_empty_string_returned_as_is(self, monkeypatch):
        monkeypatch.setenv("TEST_SECRET", "")
        assert resolve_env_secret("TEST_SECRET") == ""
