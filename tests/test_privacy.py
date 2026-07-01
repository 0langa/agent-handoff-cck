"""Tests for privacy and redaction helpers."""

from agent_handoff.privacy import (
    looks_sensitive,
    redact_tokens,
    safe_changed_files,
    scan_for_secrets,
)


def test_looks_sensitive_env() -> None:
    assert looks_sensitive(".env")
    assert looks_sensitive("config/.env.local")


def test_looks_sensitive_safe() -> None:
    assert not looks_sensitive("src/main.py")


def test_redact_tokens() -> None:
    text = "API_KEY=abc123secret"
    redacted = redact_tokens(text)
    assert "[REDACTED]" in redacted
    assert "abc123secret" not in redacted


def test_safe_changed_files_filters_env() -> None:
    files = ["src/main.py", ".env", "tests/test.py"]
    safe = safe_changed_files(files)
    assert ".env" not in safe
    assert "src/main.py" in safe


def test_scan_for_secrets() -> None:
    assert scan_for_secrets("token=abc12345678")
    assert not scan_for_secrets("hello world")
