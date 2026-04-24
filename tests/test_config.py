"""Tests for configuration loading."""

import os
from pathlib import Path

import pytest

from config import load_dotenv_file, load_settings


def test_load_dotenv_file_does_not_override_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('BITBUCKET_URL=https://old.example\nBITBUCKET_PAT=secret\n')
    monkeypatch.setenv("BITBUCKET_URL", "https://kept.example")
    monkeypatch.delenv("BITBUCKET_PAT", raising=False)
    load_dotenv_file(env_file)
    assert os.environ["BITBUCKET_URL"] == "https://kept.example"
    assert os.environ["BITBUCKET_PAT"] == "secret"


def test_load_settings_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BITBUCKET_URL", "https://bb.example/bitbucket")
    monkeypatch.setenv("BITBUCKET_PAT", "token")
    monkeypatch.setenv("BITBUCKET_FILE_PATH", "cfg/app.yaml")
    monkeypatch.setenv("BITBUCKET_HTTP_RETRIES", "3")
    monkeypatch.setenv("BITBUCKET_HTTP_BACKOFF_S", "2.5")
    monkeypatch.setenv("BITBUCKET_FLUSH_INTERVAL", "4")
    s = load_settings()
    assert s.bitbucket_url == "https://bb.example/bitbucket"
    assert s.bitbucket_pat == "token"
    assert s.file_path == "cfg/app.yaml"
    assert s.http_max_attempts == 3
    assert s.http_backoff_seconds == 2.5
    assert s.flush_interval == 4


def test_load_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BITBUCKET_URL", "https://bb.example")
    monkeypatch.setenv("BITBUCKET_PAT", "token")
    monkeypatch.delenv("BITBUCKET_HTTP_RETRIES", raising=False)
    monkeypatch.delenv("BITBUCKET_HTTP_BACKOFF_S", raising=False)
    monkeypatch.delenv("BITBUCKET_FLUSH_INTERVAL", raising=False)
    s = load_settings()
    assert s.http_max_attempts == 5
    assert s.http_backoff_seconds == 1.0
    assert s.flush_interval == 1


def test_load_settings_requires_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BITBUCKET_URL", raising=False)
    monkeypatch.setenv("BITBUCKET_PAT", "t")
    with pytest.raises(ValueError, match="BITBUCKET_URL"):
        load_settings()


def test_load_settings_requires_pat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BITBUCKET_URL", "https://bb.example")
    monkeypatch.delenv("BITBUCKET_PAT", raising=False)
    with pytest.raises(ValueError, match="BITBUCKET_PAT"):
        load_settings()
