"""CLI entrypoint."""

from __future__ import annotations

import sys

import typer

from .commands import (
    ask,
    batch,
    chat,
    code_review,
    compare,
    config_cmd,
    doctor,
    eval_cmd,
    explain_error,
    files,
    json_mode,
    logs,
    models,
    profile,
    prompt_lint,
    redact,
    replay,
)
from .errors import OpenAIPyCliError
from .output import print_error
from .runtime import options

app = typer.Typer(
    name="oai-cli",
    help="Developer-first CLI wrapper around the official OpenAI Python SDK.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


@app.callback()
def global_options(
    debug: bool = typer.Option(False, "--debug", help="Show traceback for expected errors."),
    timeout: float | None = typer.Option(None, "--timeout", help="OpenAI request timeout seconds."),
    plain: bool = typer.Option(False, "--plain", help="Prefer plain text for machine parsing."),
    json_output: bool = typer.Option(False, "--json", help="Prefer JSON for global errors."),
) -> None:
    options.debug = debug
    options.timeout = timeout
    options.plain = plain
    options.json_output = json_output

app.command("ask")(ask.ask)
app.command("redact")(redact.redact)
app.command("doctor")(doctor.doctor)
app.command("replay")(replay.replay)
app.command("compare")(compare.compare)
app.command("prompt-lint")(prompt_lint.prompt_lint)
app.command("chat")(chat.chat)
app.command("json")(json_mode.json_command)
app.command("code-review")(code_review.code_review)
app.command("explain-error")(explain_error.explain_error)
app.command("eval")(eval_cmd.eval_command)
app.add_typer(files.app, name="files")
app.add_typer(batch.app, name="batch")
app.add_typer(logs.app, name="logs")
app.add_typer(profile.app, name="profile")
app.add_typer(config_cmd.app, name="config")
app.add_typer(models.app, name="models")


def main() -> None:
    try:
        app()
    except OpenAIPyCliError as exc:
        if options.debug:
            raise
        print_error(str(exc))
        sys.exit(exc.exit_code)


if __name__ == "__main__":
    main()
