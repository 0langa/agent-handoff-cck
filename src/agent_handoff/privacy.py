"""Privacy and safety helpers for handoff capture."""

from __future__ import annotations

import re
from pathlib import Path

SENSITIVE_FILENAME_PATTERNS = (
    ".env",
    ".env.",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials",
    "token",
    "secret",
    ".htpasswd",
)

SENSITIVE_SOURCES = (
    "gmail",
    "webde",
    "email-body",
    "browser-session",
    "credential-store",
    "api-key",
    "auth-header",
)

TOKEN_RE = re.compile(
    r"([\w-]*(?:token|key|secret|password|passwd|credential|auth)[\w-]*\s*[:=]\s*)"
    r"['\"]?[A-Za-z0-9_\-./=+]{8,}['\"]?",
    re.IGNORECASE,
)


def looks_sensitive(path: str) -> bool:
    lower = path.lower()
    return any(lower.endswith(pat) or ("/" + pat) in lower or ("\\" + pat) in lower for pat in SENSITIVE_FILENAME_PATTERNS)


def redact_tokens(text: str) -> str:
    if not text:
        return text
    return TOKEN_RE.sub(r"\1[REDACTED]", text)


def safe_changed_files(paths: list[str]) -> list[str]:
    return [p for p in paths if not looks_sensitive(p)]


def safe_git_status(status: str) -> str:
    lines = status.splitlines()
    safe: list[str] = []
    for line in lines:
        stripped = line.strip().lower()
        if any(pat in stripped for pat in SENSITIVE_FILENAME_PATTERNS):
            safe.append("[sensitive file redacted]")
        else:
            safe.append(line)
    return "\n".join(safe)


def scan_for_secrets(text: str) -> bool:
    return bool(TOKEN_RE.search(text))


def describe_sensitive_source(name: str) -> str | None:
    lower = name.lower()
    for source in SENSITIVE_SOURCES:
        if source in lower:
            return source
    return None
