"""Configuration commands."""

from __future__ import annotations

from typing import Annotated

import typer

from ..config import AppConfig, Profile, config_path, load_config, write_config
from ..output import console, print_json, print_warning

app = typer.Typer(help="Initialize and inspect configuration.")


@app.command("init")
def init_config(
    force: Annotated[bool, typer.Option("--force")] = False,
    api_key_env: Annotated[str, typer.Option("--api-key-env")] = "OPENAI_API_KEY",
    model: Annotated[str, typer.Option("--model")] = "gpt-4.1-mini",
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    path = config_path()
    if path.exists() and not force:
        print_warning(f"Config already exists: {path}. Use --force to overwrite.")
        return
    cfg = AppConfig(
        default_model=model,
        api_key_env=api_key_env,
        active_profile="default",
        profiles={
            "default": Profile(api_key_env=api_key_env, default_model=model),
        },
    )
    written = write_config(cfg, path)
    data = {
        "config_path": str(written),
        "api_key_env": api_key_env,
        "next_step": f"export {api_key_env}=...",
    }
    if json_output:
        print_json(data)
    else:
        console.print(f"Wrote config: {written}")
        console.print(f"Next: export {api_key_env}=...")


@app.command("show")
def show_config(json_output: Annotated[bool, typer.Option("--json")] = False) -> None:
    cfg = load_config()
    data = cfg.model_dump(mode="json")
    data["config_path"] = str(config_path())
    if json_output:
        print_json(data)
    else:
        print_json(data)
