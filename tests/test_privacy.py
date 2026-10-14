"""Tests for privacy and redaction helpers."""

import base64

from agent_handoff.privacy import (
    is_secret_name,
    looks_sensitive,
    redact_tokens,
    safe_changed_files,
    scan_for_secrets,
)


def _assert_redacted(text: str, secret: str) -> str:
    """Check that ``secret`` is flagged and removed, and that redaction is stable."""
    assert scan_for_secrets(text), text
    redacted = redact_tokens(text)
    assert secret not in redacted, redacted
    assert "[REDACTED]" in redacted, redacted
    assert redact_tokens(redacted) == redacted, redacted
    assert not scan_for_secrets(redacted), redacted
    return redacted


def _assert_intact(text: str) -> None:
    assert not scan_for_secrets(text), text
    assert redact_tokens(text) == text


def _fake(prefix: str, length: int, alphabet: str = "aB3dE5fG7hJ9kL1mN0") -> str:
    """Build a token-shaped value at runtime, so secret scanners don't flag this file."""
    return prefix + (alphabet * length)[:length]


def _b64(data: str) -> str:
    return base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")


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


def test_redact_tokens_json_quoted_key() -> None:
    text = '{"api_key": "sk-abcdefghijklmnop1234"}'
    assert scan_for_secrets(text)
    # The value's quotes stay, so redacted JSON is still valid JSON.
    assert redact_tokens(text) == '{"api_key": "[REDACTED]"}'


def test_redact_tokens_bearer_header() -> None:
    text = "Authorization: Bearer abcdefghijklmnop1234"
    assert scan_for_secrets(text)
    assert redact_tokens(text) == "Authorization: Bearer [REDACTED]"


def test_redact_tokens_quoted_auth_header_values() -> None:
    # The scheme sits inside the quoted value in JSON, Python dicts, and YAML.
    cases = {
        '{"Authorization": "Bearer abcdefghijklmnop1234"}': "abcdefghijklmnop1234",
        "headers = {'Authorization': 'Bearer abcdefghijklmnop1234'}": "abcdefghijklmnop1234",
        'authorization: "Bearer abcdefghijklmnop1234"': "abcdefghijklmnop1234",
        '{"Authorization": "Basic dXNlcjpwYXNzd29yZA=="}': "dXNlcjpwYXNzd29yZA==",
    }
    for text, secret in cases.items():
        assert scan_for_secrets(text), text
        redacted = redact_tokens(text)
        assert secret not in redacted, redacted
        assert "[REDACTED]" in redacted, redacted
    assert (
        redact_tokens('{"Authorization": "Bearer abcdefghijklmnop1234"}')
        == '{"Authorization": "Bearer [REDACTED]"}'
    )


def test_is_secret_name_matches_the_last_word() -> None:
    secret_names = [
        "token", "api_key", "apiKey", "APIKEY", "X-Api-Key", "x_api_key", "secret",
        "client_secret", "clientSecret", "GITHUB_TOKEN", "access_token", "authToken",
        "password", "PGPASSWORD", "DB_PASS", "passwd", "credentials", "Authorization",
        "Proxy-Authorization", "auth", "basicAuth", "_auth", "secret_key", "SECRET_KEY",
        "AWS_SECRET_ACCESS_KEY", "privateKey", "AccountKey", "API_KEY_2", "token1",
    ]
    for name in secret_names:
        assert is_secret_name(name), name
    ordinary_names = [
        "tokenizer", "tokens", "token_count", "max_tokens", "token_type", "secretary",
        "secrets", "secret_name", "author", "authentication", "OAuth", "keyboard_layout",
        "primary_key", "key", "sort_key", "public_key", "monkey", "passwordless",
        "password_file", "bypass", "credential_helper", "PWD",
    ]
    for name in ordinary_names:
        assert not is_secret_name(name), name


def test_redact_tokens_secret_key_values() -> None:
    cases = {
        '{"apiKey": "abcdefghij123"}': "abcdefghij123",
        '{"access_token": "abcdefghij123"}': "abcdefghij123",
        '{"client_secret": "abcdefghij123"}': "abcdefghij123",
        '{"privateKey": "abcdefghij123"}': "abcdefghij123",
        "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY": "wJalrXUtnFEMI",
        "-H 'X-Api-Key: abcdefghij123'": "abcdefghij123",
        "PGPASSWORD=abcdefghij123 psql -h db": "abcdefghij123",
        "DB_PASS=abcdefghij123": "abcdefghij123",
        "'password' => 'hunter2hunter'": "hunter2hunter",
        # Quoted values are redacted whole, whatever their length or characters.
        '{"password": "hunter2"}': "hunter2",
        'password: "Tr0ub4dor&3xyz"': "Tr0ub4dor",
        # Escaped JSON, for example a curl body inside another string.
        '{\\"api_key\\": \\"abcdefghij123\\"}': "abcdefghij123",
    }
    for text, secret in cases.items():
        _assert_redacted(text, secret)
    assert redact_tokens('{"password": "hunter2"}') == '{"password": "[REDACTED]"}'


def test_redact_tokens_leaves_lookalike_keys_alone() -> None:
    # The old pattern matched any key containing token/key/secret/auth and redacted these.
    for text in [
        '{"tokenizer": "cl100k_base"}',
        '{"tokens": "abcdefghijkl"}',
        '{"token_count": 123456789}',
        '{"max_tokens": 16384000}',
        "--max-tokens=16384000",
        '{"secretary": "jane.doe-smith"}',
        '{"author": "0langa-bot"}',
        '{"keyboard_layout": "us-international"}',
        '{"primary_key": "user_id_column"}',
        '{"authentication": "required"}',
        '{"secret_name": "prod-db-password"}',
        "OAuth: enabled-for-everyone",
        "auth: basic validation runs first",
        "key=operator.itemgetter",
        "token_count = estimate_tokens(text)",
    ]:
        _assert_intact(text)


def test_redact_tokens_skips_placeholders() -> None:
    for text in [
        'api_key: "${API_KEY}"',
        "token=$GITHUB_TOKEN",
        "password: '${{ secrets.DB_PASSWORD }}'",
        'secret: "<your-secret>"',
        'password: "********"',
        'password: "[REDACTED]"',
        "token: none",
    ]:
        _assert_intact(text)


def test_redact_tokens_known_token_formats() -> None:
    jwt = ".".join(
        [_b64('{"alg":"HS256","typ":"JWT"}'), _b64('{"sub":"1234567890"}'), _fake("", 43)]
    )
    tokens = {
        "GitHub classic": _fake("ghp_", 36),
        "GitHub OAuth": _fake("gho_", 36),
        "GitHub user-to-server": _fake("ghu_", 36),
        "GitHub server-to-server": _fake("ghs_", 36),
        "GitHub refresh": _fake("ghr_", 36),
        "GitHub fine-grained": _fake("github_pat_", 82, "11AbCdEfGh_0123456789"),
        "OpenAI legacy": _fake("sk-", 48),
        "OpenAI project": _fake("sk-proj-", 64, "Ab3_dE5-fG7"),
        "Anthropic": _fake("sk-ant-api03-", 93, "Ab3_dE5-fG7"),
        "AWS long-term": _fake("AKIA", 16, "IOSFODNN7EXAMPLE"),
        "AWS temporary": _fake("ASIA", 16, "Q3EGJWZK7EXAMPL2"),
        "Slack bot": _fake("xoxb-", 50, "1234567890-"),
        "Slack user": _fake("xoxp-", 60, "1234567890-aBcD-"),
        "Google": _fake("AIza", 35, "SyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q"),
        "GitLab": _fake("glpat-", 20),
        "npm": _fake("npm_", 36),
        "JWT": jwt,
    }
    for kind, token in tokens.items():
        for text in [
            f"used {token} for the API",
            f"({token}).",
            f'"{token}"',
            f"curl -H 'Authorization: Bearer {token}'",
        ]:
            redacted = _assert_redacted(text, token)
            assert "[REDACTED]" in redacted, kind
    assert redact_tokens(f"push with {tokens['GitHub classic']}.") == "push with [REDACTED]."
    url = f"https://{tokens['GitHub classic']}@github.com/o/r.git"
    assert redact_tokens(url) == "https://[REDACTED]@github.com/o/r.git"


def test_redact_tokens_leaves_token_lookalikes_alone() -> None:
    for text in [
        "sk-learn and scikit-learn are the same library",
        "see the risk-assessment-for-q3-2026-planning doc",
        "sk-this-is-a-long-kebab-case-css-class-name",
        "ghp_ and github_pat_ are GitHub token prefixes; ghp_abc is too short",
        "AKIA and ASIA start AWS access key IDs",
        "xoxo, gossip girl",
        "AIza starts a Google API key",
        "eyJ is base64 for an opening brace and quote",
        "npm_config_cache and ghost_writer are plain names",
        "commit 319cab6d2f0e4a8b9c1d3e5f7a9b0c2d4e6f8a0b",
        "id 123e4567-e89b-12d3-a456-426614174000",
    ]:
        _assert_intact(text)


def test_safe_changed_files_filters_env() -> None:
    files = ["src/main.py", ".env", "tests/test.py"]
    safe = safe_changed_files(files)
    assert ".env" not in safe
    assert "src/main.py" in safe


def test_scan_for_secrets() -> None:
    assert scan_for_secrets("token=abc12345678")
    assert not scan_for_secrets("hello world")
