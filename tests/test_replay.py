from openai_py_cli.commands.replay import build_replay_payload
from openai_py_cli.logging_store import RequestLog


def test_build_replay_payload_replaces_model() -> None:
    row = RequestLog(
        id="abc",
        created_at="2026-01-01T00:00:00Z",
        command="ask",
        model="gpt-4.1-mini",
        input_text="hello",
        output_text="world",
        status="success",
        request_json='{"model":"gpt-4.1-mini","input":"hello"}',
    )
    payload = build_replay_payload(row, "gpt-4.1")
    assert payload == {"model": "gpt-4.1", "input": "hello"}


def test_build_replay_payload_falls_back_to_log_fields() -> None:
    row = RequestLog(
        id="abc",
        created_at="2026-01-01T00:00:00Z",
        command="ask",
        model="gpt-4.1-mini",
        input_text="hello",
        output_text="world",
        status="success",
    )
    assert build_replay_payload(row) == {"model": "gpt-4.1-mini", "input": "hello"}
