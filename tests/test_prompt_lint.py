from openai_py_cli.commands.prompt_lint import analyze_prompt
from openai_py_cli.redaction import contains_secrets


def test_secret_detection_for_prompt_lint_phase() -> None:
    assert contains_secrets("Use sk-abcdefghijklmnopqrstuvwxyz123456")


def test_prompt_lint_detects_missing_format_and_vague_words() -> None:
    result = analyze_prompt("Сделай красиво и быстро")
    assert result.score < 100
    assert any(
        "format" in warning.lower() or "формат" in warning.lower()
        for warning in result.warnings
    )
    assert any(
        "vague" in warning.lower() or "measurable" in warning.lower()
        for warning in result.warnings
    )
    assert "Output format" in result.improved_prompt


def test_prompt_lint_warns_json_without_schema() -> None:
    result = analyze_prompt("Extract invoice fields and return JSON")
    assert any("schema" in warning.lower() for warning in result.warnings)
