from openai_py_cli.client import ClientContext
from openai_py_cli.config import AppConfig, Profile
from openai_py_cli.dry_run import build_dry_run


def test_dry_run_hides_api_key_value() -> None:
    cfg = AppConfig()
    profile = Profile()
    context = ClientContext(cfg, "default", profile, "OPENAI_API_KEY", True)
    data = build_dry_run(
        operation="responses.create",
        model="gpt-4.1-mini",
        payload={"input": "hi"},
        redaction_enabled=True,
        context=context,
    )
    assert data["api_key_env"] == "OPENAI_API_KEY"
    assert "api_key" not in data
