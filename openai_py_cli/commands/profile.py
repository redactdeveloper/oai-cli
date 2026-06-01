"""Profile management commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from ..config import Profile, load_config, write_config
from ..output import console, print_json, print_warning

app = typer.Typer(help="Manage local OpenAI profiles.")


@app.command("list")
def list_profiles() -> None:
    cfg = load_config()
    table = Table(title="Profiles")
    table.add_column("active")
    table.add_column("name")
    table.add_column("api key env")
    table.add_column("model")
    table.add_column("base url")
    for name, profile in cfg.profiles.items():
        table.add_row(
            "*" if name == cfg.active_profile else "",
            name,
            profile.api_key_env,
            profile.default_model,
            profile.base_url or "",
        )
    console.print(table)


@app.command("use")
def use_profile(name: str) -> None:
    cfg = load_config()
    if name not in cfg.profiles:
        raise typer.BadParameter(f"Profile does not exist: {name}")
    cfg.active_profile = name
    write_config(cfg)
    console.print(f"Active profile: {name}")


@app.command("show")
def show_profile(json_output: Annotated[bool, typer.Option("--json")] = False) -> None:
    cfg = load_config()
    profile = cfg.active()
    data = {"name": cfg.active_profile, **profile.model_dump()}
    if json_output:
        print_json(data)
    else:
        print_json(data)


@app.command("create")
def create_profile(
    name: str,
    api_key_env: Annotated[str, typer.Option("--api-key-env")] = "OPENAI_API_KEY",
    model: Annotated[str, typer.Option("--model")] = "gpt-4.1-mini",
    base_url: Annotated[str | None, typer.Option("--base-url")] = None,
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", help="Not stored; prints env guidance."),
    ] = None,
) -> None:
    cfg = load_config()
    if name in cfg.profiles:
        raise typer.BadParameter(f"Profile already exists: {name}")
    if api_key:
        print_warning(
            "API keys are not stored in plaintext. Export it instead: "
            f"export {api_key_env}=..."
        )
    cfg.profiles[name] = Profile(api_key_env=api_key_env, default_model=model, base_url=base_url)
    write_config(cfg)
    console.print(f"Created profile: {name}")


@app.command("delete")
def delete_profile(name: str) -> None:
    cfg = load_config()
    if name == "default":
        raise typer.BadParameter("The default profile cannot be deleted.")
    if name not in cfg.profiles:
        raise typer.BadParameter(f"Profile does not exist: {name}")
    del cfg.profiles[name]
    if cfg.active_profile == name:
        cfg.active_profile = "default"
    write_config(cfg)
    console.print(f"Deleted profile: {name}")
