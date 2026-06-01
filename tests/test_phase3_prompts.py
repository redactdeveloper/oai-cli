from openai_py_cli.commands.code_review import build_code_review_prompt
from openai_py_cli.commands.explain_error import build_explain_error_prompt
from openai_py_cli.commands.json_mode import build_json_payload


def test_build_json_payload_includes_schema() -> None:
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    payload = build_json_payload("Extract name", schema, "gpt-4.1-mini")
    assert payload["model"] == "gpt-4.1-mini"
    assert "Return JSON only" in payload["input"]
    assert payload["text"] == {"format": {"type": "json_object"}}


def test_code_review_prompt_includes_required_sections() -> None:
    prompt = build_code_review_prompt("diff --git a/x b/x", focus="security", output="json")
    assert "security" in prompt
    assert "suggested" in prompt
    assert "Diff:" in prompt


def test_explain_error_prompt_includes_log() -> None:
    prompt = build_explain_error_prompt("Traceback line")
    assert "short cause" in prompt
    assert "Traceback line" in prompt
