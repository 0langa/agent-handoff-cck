"""Tests for privacy and redaction helpers."""

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


def test_safe_changed_files_filters_env() -> None:
    files = ["src/main.py", ".env", "tests/test.py"]
    safe = safe_changed_files(files)
    assert ".env" not in safe
    assert "src/main.py" in safe


def test_scan_for_secrets() -> None:
    assert scan_for_secrets("token=abc12345678")
    assert not scan_for_secrets("hello world")
