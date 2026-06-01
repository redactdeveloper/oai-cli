from openai_py_cli.redaction import contains_secrets, redact_text


def test_redacts_common_secrets() -> None:
    text = (
        "email me@example.com Bearer abcdef1234567890 "
        "sk-abcdefghijklmnopqrstuvwxyz123456 token=abcdef1234567890abcdef"
    )
    result = redact_text(text)
    assert "[REDACTED_EMAIL]" in result.text
    assert "Bearer [REDACTED_TOKEN]" in result.text
    assert "[REDACTED_OPENAI_KEY]" in result.text
    assert "[REDACTED_SECRET]" in result.text


def test_detects_private_key() -> None:
    text = "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----"
    assert contains_secrets(text)
    assert redact_text(text).text == "[REDACTED_PRIVATE_KEY]"
