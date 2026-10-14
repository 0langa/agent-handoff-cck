"""Tests for privacy and redaction helpers."""

import base64

from agent_handoff.privacy import (
    is_secret_name,
    looks_sensitive,
    redact_data,
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
    # Unquoted values keep special characters, including a trailing "!".
    assert redact_tokens("password=p@ssw0rd!") == "password=[REDACTED]"
    assert redact_tokens("Set password=hunter2hunter.") == "Set password=[REDACTED]."


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


def test_redact_tokens_secret_cli_flags() -> None:
    cases = {
        "mytool --token abc123def456 --verbose": "mytool --token [REDACTED] --verbose",
        "mytool --token=abc123def456": "mytool --token=[REDACTED]",
        "mytool --token=abc": "mytool --token=[REDACTED]",
        'mytool --token "s3cr3t value" next': 'mytool --token "[REDACTED]" next',
        "mytool --password hunter2": "mytool --password [REDACTED]",
        "mytool --password=hunter2": "mytool --password=[REDACTED]",
        "mytool --db-password='p@ss w0rd'": "mytool --db-password='[REDACTED]'",
        "mytool --api-key 9f8e7d6c5b4a": "mytool --api-key [REDACTED]",
        "mytool --secret Zx9Qw8Er7": "mytool --secret [REDACTED]",
        "mytool --client-secret abcXYZdef": "mytool --client-secret [REDACTED]",
        "mytool --auth-token=abcdefg --other": "mytool --auth-token=[REDACTED] --other",
        "mytool --password correcthorsebatterystaple": "mytool --password [REDACTED]",
        "vault login -token abc123def": "vault login -token [REDACTED]",
        "consul acl token list -token=abc123": "consul acl token list -token=[REDACTED]",
        "(use --token abc123).": "(use --token [REDACTED]).",
        "mytool --password Summer2024!": "mytool --password [REDACTED]",
    }
    for text, expected in cases.items():
        assert scan_for_secrets(text), text
        assert redact_tokens(text) == expected, text
        assert not scan_for_secrets(expected), expected


def test_redact_tokens_leaves_ordinary_cli_flags_alone() -> None:
    for text in [
        "mytool --max-tokens 4096",
        "mytool --tokenizer cl100k_base",
        "mytool --token-file ~/.config/token",
        "docker login --password-stdin < pw.txt",
        "pg_dump --no-password mydb",
        "mytool --token --verbose",
        "mytool --secretary-name Jane",
        # Prose and placeholders after a space-separated flag.
        "use the --token flag",
        "pass --token instead of the env var",
        "run --password manually, then --token later.",
        "pass --token TOKEN or --api-key YOUR_API_KEY",
        "gh --token $GITHUB_TOKEN",
        "gh --token ${{ secrets.GITHUB_TOKEN }}",
        "mytool --password <your-password>",
    ]:
        _assert_intact(text)


def test_redact_tokens_url_credentials() -> None:
    cases = {
        "git clone https://deploy:hunter2pass@git.example.com/team/repo.git":
            "git clone https://deploy:[REDACTED]@git.example.com/team/repo.git",
        "DATABASE_URL=postgres://admin:S3cr3t!@db.internal:5432/app":
            "DATABASE_URL=postgres://admin:[REDACTED]@db.internal:5432/app",
        "redis://:p%40ssw0rd@cache:6379/0": "redis://:[REDACTED]@cache:6379/0",
        "https://user:p@ss@host.example.com/path": "https://user:[REDACTED]@host.example.com/path",
        "mongodb+srv://app:Zx9Qw8@cluster0.mongodb.net/db?retryWrites=true":
            "mongodb+srv://app:[REDACTED]@cluster0.mongodb.net/db?retryWrites=true",
        "jdbc:postgresql://svc:pw12345@db:5432/app": "jdbc:postgresql://svc:[REDACTED]@db:5432/app",
        '"url": "https://bot:t0ken@api.example.com/v1"':
            '"url": "https://bot:[REDACTED]@api.example.com/v1"',
        "ftp://anonymous:guest@ftp.example.com/pub": "ftp://anonymous:[REDACTED]@ftp.example.com/pub",
    }
    for text, expected in cases.items():
        assert scan_for_secrets(text), text
        assert redact_tokens(text) == expected, text
        assert not scan_for_secrets(expected), expected


def test_redact_tokens_leaves_urls_without_passwords_alone() -> None:
    for text in [
        "https://example.com:8443/path",
        "ssh://git@github.com/o/r.git",
        "git@github.com:o/r.git",
        "mailto:someone@example.com",
        "http://localhost:3000/login?next=/a@b",
        "see https://example.com/a:b@c for details",
        "postgres://user:${DB_PASSWORD}@db/app",
        "postgres://user:****@db/app",
    ]:
        _assert_intact(text)


def test_redact_tokens_cookie_headers() -> None:
    # Cookie values go; cookie names and Set-Cookie attributes stay readable.
    cases = {
        "Cookie: sessionid=abc123def456; theme=dark":
            "Cookie: sessionid=[REDACTED]; theme=[REDACTED]",
        "Set-Cookie: sid=Zx9Qw8Er7Ty6; Path=/; Expires=Wed, 21 Oct 2026 07:28:00 GMT; HttpOnly":
            "Set-Cookie: sid=[REDACTED]; Path=/; Expires=Wed, 21 Oct 2026 07:28:00 GMT; HttpOnly",
        'curl -H "Cookie: sid=abc123def456" https://example.com':
            'curl -H "Cookie: sid=[REDACTED]" https://example.com',
        '{"Cookie": "sid=abc123def456; lang=de", "Accept": "text/html"}':
            '{"Cookie": "sid=[REDACTED]; lang=[REDACTED]", "Accept": "text/html"}',
        "headers = {'Set-Cookie': 'token=abc; Path=/'}":
            "headers = {'Set-Cookie': 'token=[REDACTED]; Path=/'}",
        # HTTP/2 header dumps use lower-case names.
        "  cookie: _ga=GA1.2.3; csrftoken=Zx9Qw8":
            "  cookie: _ga=[REDACTED]; csrftoken=[REDACTED]",
        "curl -b 'sid=abc123; lang=en' https://x": "curl -b 'sid=[REDACTED]; lang=[REDACTED]' https://x",
        "curl --cookie=sid=abc123 https://x": "curl --cookie=sid=[REDACTED] https://x",
    }
    for text, expected in cases.items():
        assert scan_for_secrets(text), text
        assert redact_tokens(text) == expected, text
        assert not scan_for_secrets(expected), expected
    assert redact_data(
        {"Cookie": "sid=abc123def456", "Set-Cookie": ["a=1; Path=/", "b=2"], "cookie_jar": "x.txt"}
    ) == {"Cookie": "sid=[REDACTED]", "Set-Cookie": ["a=[REDACTED]; Path=/", "b=[REDACTED]"],
          "cookie_jar": "x.txt"}


def test_redact_tokens_leaves_cookie_prose_alone() -> None:
    for text in [
        "I baked a cookie: it was great",
        "set the cookie: theme=dark before testing",
        "The Cookie header carries sid=... values",
        "    cookie: http.cookies.BaseCookie[str] = http.cookies.SimpleCookie()",
        "Cookie: sid=<session-id>",
        "Cookie: sid=${SESSION_ID}",
        "curl -b cookies.txt -c cookies.txt https://x",
    ]:
        _assert_intact(text)


def _pem(label: str, body: str) -> str:
    """Build a PEM block at runtime, so secret scanners don't flag this file."""
    return f"-----BEGIN {label}-----\n{body}\n-----END {label}-----"


def test_redact_tokens_pem_private_keys() -> None:
    line = _fake("MIIEvQIBADANBgkqhkiG9w0BAQEFAASC", 32)
    body = f"{line}\n{line}\n{line[:20]}=="
    for label in [
        "PRIVATE KEY",
        "RSA PRIVATE KEY",
        "EC PRIVATE KEY",
        "OPENSSH PRIVATE KEY",
        "ENCRYPTED PRIVATE KEY",
        "PGP PRIVATE KEY BLOCK",
    ]:
        text = f"key:\n{_pem(label, body)}\nnext line"
        redacted = _assert_redacted(text, line)
        assert redacted == f"key:\n{_pem(label, '[REDACTED]')}\nnext line", redacted
    # A key inside a JSON string keeps its escaped line breaks.
    escaped = '{"key": "' + _pem("PRIVATE KEY", body).replace("\n", "\\n") + '\\n"}'
    assert _assert_redacted(escaped, line) == (
        '{"key": "' + _pem("PRIVATE KEY", "[REDACTED]").replace("\n", "\\n") + '\\n"}'
    )
    # A key cut off before its END line is still redacted.
    truncated = f"-----BEGIN RSA PRIVATE KEY-----\n{line}\n{line}\n"
    assert _assert_redacted(truncated, line) == "-----BEGIN RSA PRIVATE KEY-----\n[REDACTED]\n"


def test_redact_tokens_leaves_pem_lookalikes_alone() -> None:
    line = _fake("MIIDdzCCAl+gAwIBAgIEbXxXrjANBgkqhkiG9w0B", 32)
    for text in [
        _pem("CERTIFICATE", f"{line}\n{line}"),
        _pem("PUBLIC KEY", f"{line}\n{line}"),
        (
            "Keys start with -----BEGIN RSA PRIVATE KEY----- and end with "
            "-----END RSA PRIVATE KEY-----."
        ),
        _pem("PRIVATE KEY", "..."),
    ]:
        _assert_intact(text)


def test_redact_tokens_curl_user_credentials() -> None:
    cases = {
        "curl -u alice:s3cr3tPass https://api.example.com":
            "curl -u alice:[REDACTED] https://api.example.com",
        "curl -s -u 'bob:p@ss word' https://x": "curl -s -u 'bob:[REDACTED]' https://x",
        'curl --user "carol:hunter2!" https://x': 'curl --user "carol:[REDACTED]" https://x',
        "curl --user=dave:Zx9Qw8 https://x": "curl --user=dave:[REDACTED] https://x",
        "curl -ualice:pw123456 https://x": "curl -ualice:[REDACTED] https://x",
        "curl -U proxyuser:proxypass99 https://x": "curl -U proxyuser:[REDACTED] https://x",
        "curl.exe -u admin:1234 http://router": "curl.exe -u admin:[REDACTED] http://router",
        # Continued shell lines belong to the same command.
        "curl https://x \\\n  -u alice:secret99": "curl https://x \\\n  -u alice:[REDACTED]",
    }
    for text, expected in cases.items():
        assert scan_for_secrets(text), text
        assert redact_tokens(text) == expected, text
        assert not scan_for_secrets(expected), expected


def test_redact_tokens_leaves_other_user_flags_alone() -> None:
    for text in [
        "docker run -u 1000:1000 image",
        "docker run --user 1000:1000 image",
        "curl -u alice https://x",
        "curl -u : --negotiate https://x",
        "curl -u $USER:$PASS https://x",
        "curl -u alice:${TOKEN} https://x",
        "curl -u alice:<password> https://x",
        "curl --user-agent 'Mozilla/5.0 (X11; Linux:x86)' https://x",
        "use curl -u to pass credentials",
        "curl https://x\n-u alice:not-part-of-curl",
    ]:
        _assert_intact(text)


def test_redact_tokens_password_prose() -> None:
    cases = {
        "the password is hunter2": "the password is [REDACTED]",
        "The admin password is Sommer2024! now.": "The admin password is [REDACTED] now.",
        "password for postgres is pg_pass_99.": "password for postgres is [REDACTED].",
        "The passphrase was CorrectHorse": "The passphrase was [REDACTED]",
        "the password is now Xy7abcde": "the password is now [REDACTED]",
        "Das Passwort ist Geheim123": "Das Passwort ist [REDACTED]",
        "Das Kennwort lautet: Xy7!abcd": "Das Kennwort lautet: [REDACTED]",
        'the password is "s3cret!"': 'the password is "[REDACTED]"',
    }
    for text, expected in cases.items():
        assert scan_for_secrets(text), text
        assert redact_tokens(text) == expected, text
        assert not scan_for_secrets(expected), expected


def test_redact_tokens_leaves_password_prose_alone() -> None:
    for text in [
        "the password is wrong",
        "the password is correct, login works",
        "the password is still the old one",
        "password is 8 characters long",
        "the password is in the vault",
        "the password is required",
        "the password was reset yesterday",
        "password is $DB_PASSWORD",
        "the password is <your-password>",
        "Das Passwort ist falsch",
        "Das Passwort ist abgelaufen",
        "a passwordless login is set up",
    ]:
        _assert_intact(text)


def test_redact_data_walks_json_like_values() -> None:
    data = {
        "title": "use GITHUB_TOKEN=abcdefgh12345",
        "items": ["mytool --password hunter2", 3, None, True],
        "nested": {"api_key": "x1", "max_tokens": "16384000", "token": "${TOKEN}"},
        "password": "hunter2",
    }
    assert redact_data(data) == {
        "title": "use GITHUB_TOKEN=[REDACTED]",
        "items": ["mytool --password [REDACTED]", 3, None, True],
        "nested": {"api_key": "[REDACTED]", "max_tokens": "16384000", "token": "${TOKEN}"},
        "password": "[REDACTED]",
    }


def test_safe_changed_files_filters_env() -> None:
    files = ["src/main.py", ".env", "tests/test.py"]
    safe = safe_changed_files(files)
    assert ".env" not in safe
    assert "src/main.py" in safe


def test_scan_for_secrets() -> None:
    assert scan_for_secrets("token=abc12345678")
    assert not scan_for_secrets("hello world")
