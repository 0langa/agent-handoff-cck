"""Privacy and safety helpers for handoff capture."""

from __future__ import annotations

import re
from typing import Any

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
_CLOSERS = {")": "(", "]": "[", "}": "{"}
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


# `scheme://user:password@host`. Only the password is redacted; the user name stays,
# because it is usually not secret and helps the next agent (`postgres`, `oauth2`).
# The password may contain `@`; the last `@` before the host ends it.
_URL_CREDENTIALS_RE = re.compile(
    r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s:/?#@'\"<>]*:(?P<password>[^\s/?#'\"<>]+)@"
)

# `--token VALUE`, `--token=VALUE` and Go-style `-token VALUE`. Only the flag and the
# separator are consumed.
_FLAG_RE = re.compile(r"(?<![\w-])--?(?P<name>[A-Za-z][\w.-]*)(?P<sep>=|[ \t]+)")
# The shell word after a flag. Braces and brackets stay in, so `${VAR}` is one word.
_FLAG_WORD_RE = re.compile(r"""[^\s'"`,;&|<>]+""")

# `Cookie:` and `Set-Cookie:` headers at the start of a line or right after a quote, as
# in raw HTTP, `curl -H "Cookie: ..."` and JSON or Python header maps. Prose such as
# "the cookie: ..." in the middle of a sentence does not match.
_COOKIE_HEADER_RE = re.compile(
    r"""(?:^|(?<=["'`]))[ \t]*(?P<name>(?:set-)?cookie)\\?["']?[ \t]*:[ \t]*""",
    re.IGNORECASE | re.MULTILINE,
)
# One `name=value` pair of a cookie header: a cookie-name token right before `=`, so a
# Python annotation such as `cookie: SimpleCookie = SimpleCookie()` does not match.
# The value ends at `;`, a quote or the end of the line.
_COOKIE_PAIR_RE = re.compile(r"""(?P<name>[!#$%&*+.^_|~0-9A-Za-z-]+)=(?P<value>[^;\r\n"'\\]*)""")
# Set-Cookie attributes are not secret and help the next agent.
_COOKIE_ATTRIBUTES = frozenset(
    {"path", "domain", "expires", "max-age", "samesite", "priority", "version", "comment"}
)

# PEM private keys: RSA, EC, DSA, OpenSSH, PKCS#8, encrypted and PGP. The BEGIN and END
# lines stay, the key material between them is redacted. Public keys and certificates
# are not secret and do not match.
_PEM_BEGIN_RE = re.compile(r"-----BEGIN (?P<label>(?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?)-----")
# Key material without an END line, as in a cut-off log: base64 lines, also with JSON
# `\n` escapes between them.
_PEM_TRUNCATED_BODY_RE = re.compile(r"(?:[A-Za-z0-9+/=\s]|\\[nr])*")
# Real key material always has a long base64 run; a sentence that only names the
# BEGIN and END lines does not.
_PEM_MATERIAL_RE = re.compile(r"[A-Za-z0-9+/]{40,}")
_PEM_PADDING_RE = re.compile(r"(?:\s|\\[nr])*")

# A curl command, including lines continued with `\` (sh), a backtick (PowerShell) or
# `^` (cmd). `-u`, `--user`, `-U` and `--proxy-user` are only credentials there:
# `docker run -u 1000:1000` is a user and group id.
_CURL_RE = re.compile(r"(?<![\w.-])curl(?:\.exe)?(?![\w.-])(?:[\\`^]\r?\n|[^\n])*")
_CURL_USER_RE = re.compile(r"(?<![\w-])(?:--(?:proxy-)?user(?:=|[ \t]+)|-[uU][ \t]*)")
_CURL_COOKIE_RE = re.compile(r"(?<![\w-])(?:--cookie(?:=|[ \t]+)|-b[ \t]*)")

# Best effort for prose: "the password is hunter2", "Passwort lautet Sommer2024!".
# The value must look like a credential, so "the password is wrong" stays intact.
_PROSE_PASSWORD_RE = re.compile(
    r"\b(?:password|passwd|passphrase|passcode|passwort|kennwort)"
    r"(?:[ \t]+(?:for|of|on|f(?:\u00fc|ue)r|von)[ \t]+[^\s:=]+)?"
    # Longer phrases first: "is now X" must not stop at "is".
    r"[ \t]+(?:is[ \t]+now|is[ \t]+still|is[ \t]+set[ \t]+to|is|was|set[ \t]+to|changed[ \t]+to"
    r"|ist[ \t]+jetzt|ist|war|lautet)"
    r"[ \t]*:?[ \t]+",
    re.IGNORECASE,
)
_MIN_PROSE_LEN = 6


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
    """Tell a credential from a prose word, as in "use the --token flag"."""
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
    return pos, pos + len(_strip_trailing_punctuation(word.group())), False, scheme is not None


def _strip_trailing_punctuation(word: str) -> str:
    """Drop sentence punctuation and unbalanced closing brackets: `abc123).` -> `abc123`.

    A trailing `!` stays part of the value, because passwords often end in one.
    """
    while word and word[-1] in ".:?)]}":
        opener = _CLOSERS.get(word[-1])
        if opener and word.count(opener) >= word.count(word[-1]):
            break
        word = word[:-1]
    return word


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


def _flag_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for match in _FLAG_RE.finditer(text):
        name = match.group("name")
        if name.lower().startswith(("no-", "no_")) or not is_secret_name(name):
            continue
        found = _value_at(text, match.end(), _FLAG_WORD_RE)
        if found is None:
            continue
        start, end, quoted, _ = found
        value = text[start:end]
        if not value or _is_placeholder(value):
            continue
        # `--token=x` always binds a value. After a space, the next word may be prose
        # ("pass --token instead") or another flag, so it has to look like a credential.
        if match.group("sep") != "=" and not quoted and (
            value.startswith("-") or not _looks_like_credential(value)
        ):
            continue
        spans.append((start, end))
    return spans


def _cookie_pair_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """Spans of the cookie values in ``text[start:end]``; names and attributes stay."""
    spans = []
    for match in _COOKIE_PAIR_RE.finditer(text, start, end):
        value = match.group("value").rstrip()
        if (
            not value
            or match.group("name").lower() in _COOKIE_ATTRIBUTES
            or _is_placeholder(value)
        ):
            continue
        spans.append((match.start("value"), match.start("value") + len(value)))
    return spans


def _cookie_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for match in _COOKIE_HEADER_RE.finditer(text):
        start = match.end()
        quote = next((q for q in _QUOTES if text.startswith(q, start)), "")
        start += len(quote)
        # A quoted value ends at its closing quote; a header inside a quoted string
        # (`-H "Cookie: a=b"`) ends at that string's quote; a raw header at the line end.
        stops = [quote] if quote else ['"', "'", "`"]
        end = min(
            (i for i in (text.find(stop, start) for stop in [*stops, "\n"]) if i != -1),
            default=len(text),
        )
        spans += _cookie_pair_spans(text, start, end)
    return spans


def _pem_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for match in _PEM_BEGIN_RE.finditer(text):
        start = match.end()
        end = text.find(f"-----END {match.group('label')}-----", start)
        if end == -1:
            body = _PEM_TRUNCATED_BODY_RE.match(text, start)
            end = body.end() if body else start
        if not _PEM_MATERIAL_RE.search(text, start, end):
            continue
        # Keep the line breaks around the key material, so the block keeps its shape.
        start = _PEM_PADDING_RE.match(text, start).end()
        while end > start and (text[end - 1].isspace() or text[end - 2 : end] in ("\\n", "\\r")):
            end -= 1 if text[end - 1].isspace() else 2
        spans.append((start, end))
    return spans


def _curl_spans(text: str) -> list[tuple[int, int]]:
    """`curl -u user:password` and `curl --cookie "name=value"`."""
    spans = []
    for command in _CURL_RE.finditer(text):
        for match in _CURL_USER_RE.finditer(text, command.start(), command.end()):
            found = _value_at(text, match.end(), _FLAG_WORD_RE)
            if found is None:
                continue
            start, end, _, _ = found
            colon = text.find(":", start, end)
            # `-u user` makes curl ask for the password; `-u :` means no password.
            if colon == -1 or colon + 1 == end or _is_placeholder(text[colon + 1 : end]):
                continue
            spans.append((colon + 1, end))
        for match in _CURL_COOKIE_RE.finditer(text, command.start(), command.end()):
            found = _value_at(text, match.end(), _FLAG_WORD_RE)
            # Without `=` the value is a cookie jar file name.
            if found is not None and "=" in text[found[0] : found[1]]:
                spans += _cookie_pair_spans(text, found[0], found[1])
    return spans


def _prose_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for match in _PROSE_PASSWORD_RE.finditer(text):
        found = _value_at(text, match.end(), _BARE_VALUE_RE)
        if found is None:
            continue
        start, end, _, _ = found
        value = text[start:end]
        if (
            len(value) >= _MIN_PROSE_LEN
            and _looks_like_credential(value)
            and not _is_placeholder(value)
        ):
            spans.append((start, end))
    return spans


def _secret_spans(text: str) -> list[tuple[int, int]]:
    """Return the sorted, merged spans of every secret value in ``text``."""
    spans = [m.span() for m in _KNOWN_TOKEN_RE.finditer(text)]
    spans += [
        m.span("password")
        for m in _URL_CREDENTIALS_RE.finditer(text)
        if not _is_placeholder(m.group("password"))
    ]
    spans += _assignment_spans(text)
    spans += _flag_spans(text)
    spans += _cookie_spans(text)
    spans += _pem_spans(text)
    spans += _curl_spans(text)
    spans += _prose_spans(text)
    return _merge(spans)


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _replace_spans(text: str, spans: list[tuple[int, int]]) -> str:
    parts: list[str] = []
    last = 0
    for start, end in spans:
        parts += [text[last:start], REDACTED]
        last = end
    parts.append(text[last:])
    return "".join(parts)


def looks_sensitive(path: str) -> bool:
    lower = path.lower()
    return any(lower.endswith(pat) or ("/" + pat) in lower or ("\\" + pat) in lower for pat in SENSITIVE_FILENAME_PATTERNS)


def redact_tokens(text: str) -> str:
    """Replace secret-looking values in ``text`` with ``[REDACTED]``."""
    if not text:
        return text
    spans = _secret_spans(text)
    return _replace_spans(text, spans) if spans else text


def _redact_cookie_header(value: str) -> str:
    """Redact a `Cookie` or `Set-Cookie` header value stored without its header name."""
    spans = _cookie_pair_spans(value, 0, len(value)) + _secret_spans(value)
    return _replace_spans(value, _merge(spans)) if spans else value


def redact_data(value: Any) -> Any:
    """Redact JSON-like data: every string, and any string stored under a secret name."""
    if isinstance(value, str):
        return redact_tokens(value)
    if isinstance(value, dict):
        return {key: _redact_entry(key, item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_data(item) for item in value]
    return value


def _redact_entry(key: Any, item: Any) -> Any:
    if isinstance(key, str) and key.lower() in ("cookie", "set-cookie"):
        if isinstance(item, str):
            return _redact_cookie_header(item)
        if isinstance(item, (list, tuple)):  # several Set-Cookie headers
            return [_redact_cookie_header(v) if isinstance(v, str) else redact_data(v) for v in item]
    if (
        isinstance(key, str)
        and isinstance(item, str)
        and item
        and is_secret_name(key)
        and not _is_placeholder(item)
    ):
        return REDACTED
    return redact_data(item)


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
