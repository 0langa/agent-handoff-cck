"""Privacy and safety helpers for handoff capture."""

from __future__ import annotations

import re

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

REDACTED = "[REDACTED]"

# --- Secret names -----------------------------------------------------------------
# A key, header, variable or CLI flag name is a secret name when its *last word* is a
# secret word. Names split into words on `_`, `-`, `.` and camelCase, so `api_key`,
# `X-Api-Key`, `apiKey`, `GITHUB_TOKEN` and `PGPASSWORD` are secret names, while
# `tokenizer`, `tokens`, `max_tokens`, `token_count`, `secretary`, `author` and
# `primary_key` are not.

# A last word that ends in one of these is secret: `token`, `authtoken`, `PGPASSWORD`.
_SECRET_SUFFIXES = (
    "token",
    "secret",
    "password",
    "passwd",
    "passphrase",
    "credential",
    "credentials",
    "authorization",
)
# Whole words only, because ordinary words end in them (`oauth`, `bypass`).
_SECRET_WORDS = frozenset({"auth", "pass"})
# A bare `key` is too common (`primary_key`, `sort(key=...)`), so it needs one of these
# in front: `api_key`, `apiKey`, `APIKEY`, `secret_key`, `AccountKey`.
_KEY_QUALIFIERS = (
    "access",
    "account",
    "api",
    "app",
    "auth",
    "client",
    "consumer",
    "deploy",
    "encryption",
    "hmac",
    "jwt",
    "license",
    "master",
    "priv",
    "private",
    "secret",
    "service",
    "session",
    "shared",
    "signing",
    "ssh",
    "storage",
    "subscription",
    "webhook",
)
_WORD_BREAK_RE = re.compile(r"[\W_]+|(?<=[a-z0-9])(?=[A-Z])")
_TRAILING_DIGITS_RE = re.compile(r"\d+$")

# --- Values -----------------------------------------------------------------------
# Unquoted values shorter than this are left alone, so prose such as "token: none"
# stays readable. Quoted values are redacted at any length.
_MIN_BARE_LEN = 8
# An unquoted value ends at whitespace, a quote, or a delimiter that ends a value in
# URLs, JSON, YAML flow maps and shell pipelines.
_BARE_VALUE_RE = re.compile(r"""[^\s'"`,;&|<>(){}\[\]]+""")
_TRAILING_PUNCT_RE = re.compile(r"[.:!?)\]}]+$")
# Escaped quotes first, so `{\"api_key\": \"...\"}` inside a JSON string works too.
_QUOTES = ('\\"', "\\'", '"', "'")
# HTTP auth schemes stay visible: `Authorization: Bearer [REDACTED]`.
_SCHEME_RE = re.compile(r"(?:bearer|basic|token)[ \t]+", re.IGNORECASE)
# Values that only point at a secret, or were redacted already.
_PLACEHOLDER_RE = re.compile(
    r"\[REDACTED\]"
    r"|\$[({].*"  # ${VAR}, ${{ secrets.X }}, $(command)
    r"|\$(?:env:)?[A-Za-z_]\w*"  # $VAR, $env:VAR
    r"|%[A-Za-z_]\w*%"  # %VAR%
    r"|<[^<>]+>"  # <your-token>
    r"|\{\{.*\}\}"  # {{ template }}
    r"|(?P<mask>[*xX.#-])(?P=mask)*",  # ****, xxxx
    re.DOTALL,
)

# Credential formats that are secret on their own, with no key in front. Each one is
# anchored on a distinctive prefix plus a minimum length, so ordinary words such as
# `sk-learn`, `xoxo` or a lone `AKIA` do not match.
_KNOWN_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:"
    r"gh[pousr]_[A-Za-z0-9]{20,}"  # GitHub: ghp_, gho_, ghu_, ghs_, ghr_
    r"|github_pat_[A-Za-z0-9_]{20,}"  # GitHub fine-grained PAT
    r"|sk-ant-[A-Za-z0-9_-]{20,}"  # Anthropic
    r"|sk-(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{20,}"  # OpenAI style: sk-..., sk-proj-...
    r"|(?:AKIA|ASIA)[A-Z0-9]{16}"  # AWS access key ID
    r"|(?:xoxe\.)?xox[abeoprs]-[A-Za-z0-9-]{10,}"  # Slack
    r"|AIza[A-Za-z0-9_-]{35}"  # Google API key
    r"|glpat-[A-Za-z0-9_-]{20,}"  # GitLab PAT
    r"|npm_[A-Za-z0-9]{36}"  # npm
    r"|eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*"  # JWT
    r")(?![A-Za-z0-9])"
)

# `name: value`, `name=value` or `name => value`, with optional quotes around the name,
# as in JSON, YAML, .env files, HTTP headers and Python dicts. Only the name and the
# separator are consumed, so the value is still scanned for secrets of its own.
_ASSIGNMENT_RE = re.compile(
    r"(?<![\w./-])(?P<name>[A-Za-z_][\w.-]*)\\?[\"']?[ \t]*(?:=>|:=|[:=])[ \t]*"
)


def is_secret_name(name: str) -> bool:
    """Return True when a key, header, variable or flag name names a secret."""
    words = [
        word
        for word in (_TRAILING_DIGITS_RE.sub("", w).lower() for w in _WORD_BREAK_RE.split(name))
        if word
    ]
    if not words:
        return False
    last = words[-1]
    if last in _SECRET_WORDS or last.endswith(_SECRET_SUFFIXES):
        return True
    if last == "key":
        return len(words) > 1 and words[-2].endswith(_KEY_QUALIFIERS)
    return last.endswith("key") and last[:-3].endswith(_KEY_QUALIFIERS)


def _is_placeholder(value: str) -> bool:
    return _PLACEHOLDER_RE.fullmatch(value.strip()) is not None


def _looks_like_credential(word: str) -> bool:
    """Tell a credential from a prose word, for bare words after an auth scheme."""
    return (
        len(word) >= 16
        or any(c.isdigit() for c in word)
        or (any(c.islower() for c in word) and any(c.isupper() for c in word))
        or re.search(r"[^A-Za-z0-9_-]", word) is not None
    )


def _value_at(
    text: str, pos: int, word_re: re.Pattern[str]
) -> tuple[int, int, bool, bool] | None:
    """Find the value that starts at ``pos``.

    Returns ``(start, end, quoted, after_scheme)``. Quotes and a leading auth scheme stay
    outside the span, so redacted JSON stays valid and `Bearer` stays readable.
    """
    quote = next((q for q in _QUOTES if text.startswith(q, pos)), "")
    pos += len(quote)
    scheme = _SCHEME_RE.match(text, pos)
    if scheme:
        pos = scheme.end()
    if quote:
        end = text.find(quote, pos)
        newline = text.find("\n", pos)
        if end == -1 or -1 < newline < end:  # unterminated: stop at the end of the line
            end = len(text) if newline == -1 else newline
        return pos, end, True, scheme is not None
    word = word_re.match(text, pos)
    if word is None:
        return None
    end = pos + len(_TRAILING_PUNCT_RE.sub("", word.group()))
    return pos, end, False, scheme is not None


def _assignment_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for match in _ASSIGNMENT_RE.finditer(text):
        if not is_secret_name(match.group("name")):
            continue
        found = _value_at(text, match.end(), _BARE_VALUE_RE)
        if found is None:
            continue
        start, end, quoted, after_scheme = found
        value = text[start:end]
        if not value or _is_placeholder(value):
            continue
        if not quoted and (
            len(value) < _MIN_BARE_LEN or (after_scheme and not _looks_like_credential(value))
        ):
            continue
        spans.append((start, end))
    return spans


def _secret_spans(text: str) -> list[tuple[int, int]]:
    """Return the sorted, merged spans of every secret value in ``text``."""
    spans = [m.span() for m in _KNOWN_TOKEN_RE.finditer(text)]
    spans += _assignment_spans(text)
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def looks_sensitive(path: str) -> bool:
    lower = path.lower()
    return any(lower.endswith(pat) or ("/" + pat) in lower or ("\\" + pat) in lower for pat in SENSITIVE_FILENAME_PATTERNS)


def redact_tokens(text: str) -> str:
    """Replace secret-looking values in ``text`` with ``[REDACTED]``."""
    if not text:
        return text
    spans = _secret_spans(text)
    if not spans:
        return text
    parts: list[str] = []
    last = 0
    for start, end in spans:
        parts += [text[last:start], REDACTED]
        last = end
    parts.append(text[last:])
    return "".join(parts)


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
    """Return True when ``redact_tokens`` would change ``text``."""
    return bool(text) and bool(_secret_spans(text))


def describe_sensitive_source(name: str) -> str | None:
    lower = name.lower()
    for source in SENSITIVE_SOURCES:
        if source in lower:
            return source
    return None
