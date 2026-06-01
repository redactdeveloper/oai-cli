# oai-cli
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![PyPI](https://img.shields.io/badge/PyPI-3775A9?style=for-the-badge&logo=pypi&logoColor=white)
![MIT License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)

Developer-first CLI for the OpenAI API, built on top of the official `openai-python` SDK.

`oai-cli` is designed for day-to-day engineering work: quick prompts, dry-run payload inspection, local request logs, model comparisons, JSON schema validation, file and batch helpers, prompt linting, redaction, and AI-assisted review workflows from pipes.

## Highlights

- One-shot prompts with the Responses API: `oai-cli ask`
- Interactive streaming chat REPL: `oai-cli chat`
- Safe payload previews with `--dry-run`
- Local SQLite request history, replay, export, and secret scanning
- Local redaction for API keys, bearer tokens, JWTs, emails, phone numbers, cookies, private keys, and tokenized URLs
- Prompt linting without API calls
- Model comparison and eval runs across multiple models
- Strict JSON mode with JSON Schema validation
- Files and Batch API helpers
- Pipe-friendly code review and traceback explanation commands
- Profiles that store environment variable names, not plaintext API keys

## Requirements

- Python `3.10`, `3.11`, or `3.12`
- An OpenAI API key exported through an environment variable

Python `3.13+` is intentionally not advertised yet because several upstream dependencies may be unstable there.

## Installation

From PyPI:

```bash
pip install oai-workbench-cli
```

The installed console command is still `oai-cli`.

For isolated CLI installation:

```bash
pipx install oai-workbench-cli
```

From a local checkout:

```bash
cd /path/to/oai-cli
pip install .
```

For development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quickstart

```bash
export OPENAI_API_KEY=...

oai-cli config init
oai-cli doctor --check-api
oai-cli ask --no-stream "Reply with OK only."
oai-cli ask --dry-run "Explain this payload"
```

Fish shell:

```fish
set -gx OPENAI_API_KEY 'your_key_here'
oai-cli doctor --check-api
```

Do not paste API keys into issues, chats, shell history, or committed files.

## Global Options

Global options must appear before the command:

```bash
oai-cli --timeout 30 ask "Reply briefly"
oai-cli --plain doctor
oai-cli --json doctor
oai-cli --debug ask "Show traceback for expected CLI errors"
```

`--debug` can show tracebacks. Use it locally and avoid sharing output that may include sensitive data.

## Configuration

Initialize config:

```bash
oai-cli config init
oai-cli config show
```

Default config paths:

- Linux/macOS: `~/.config/oai-cli/config.toml`
- Windows: platform app config directory via `platformdirs`

The CLI stores the name of the environment variable, not the API key value.

Profiles:

```bash
oai-cli profile list
oai-cli profile create work --api-key-env OPENAI_WORK_API_KEY --model gpt-4.1
oai-cli profile use work
oai-cli profile show
oai-cli profile delete work
```

Supported config fields:

- `default_model`
- `api_key_env`
- `base_url`
- `organization`
- `project`
- `log_enabled`
- `log_path`
- `redact_enabled`
- `active_profile`
- `profiles`

## Ask

```bash
oai-cli ask "Explain Python context managers"
cat prompt.txt | oai-cli ask --model gpt-4.1-mini
oai-cli ask --system "You are concise." --temperature 0.2 "Summarize this"
oai-cli ask --dry-run "Show request payload only"
oai-cli ask --cost-estimate "Estimate input cost"
```

Key options:

- `--model`, `-m`: override the active profile's default model for this request.
- `--system`: add system/developer instructions for the request.
- `--temperature`: control sampling randomness. Lower values are more deterministic.
- `--max-output-tokens`: cap the response length.
- `--stream / --no-stream`: stream output live or wait for the full response.
- `--json`: request JSON object output from the model.
- `--dry-run`: print the endpoint, profile, redaction status, and request payload without calling the API.
- `--cost-estimate`: estimate input token count and best-effort cost before sending.
- `--save / --no-save`: enable or skip saving the request to local SQLite logs.
- `--redact / --no-redact`: locally redact likely secrets before sending, or explicitly disable redaction.

## Chat

```bash
oai-cli chat --model gpt-4.1-mini
```

REPL commands:

```text
/help
/exit
/clear
/model <name>
/system <text>
/save <name>
/load <name>
/history
```

For multiline input, enter `"""`, then type lines, then close with `"""`.

## Redaction

```bash
oai-cli redact "Bearer abcdef1234567890"
cat file.txt | oai-cli redact
cat file.txt | oai-cli redact --json
```

Redaction is local. It detects common secrets including OpenAI keys, JWTs, bearer tokens, GitHub tokens, generic API keys, cookies, private key PEM blocks, emails, phone numbers, and query-string tokens.

## Logs And Replay

```bash
oai-cli logs list
oai-cli logs show <id>
oai-cli logs export --format jsonl
oai-cli logs scan-secrets
oai-cli replay <id> --dry-run
oai-cli replay <id> --model gpt-4.1 --yes
```

Logs are stored in SQLite under the platform data directory unless `log_path` is configured.

## Compare

```bash
oai-cli compare "Summarize this release note" -m gpt-4.1-mini -m gpt-4.1
oai-cli compare --dry-run "Show payload only" -m gpt-4.1-mini -m gpt-4.1
oai-cli compare "Prompt" -m gpt-4.1-mini -m gpt-4.1 --diff
oai-cli compare "Prompt" -m gpt-4.1-mini -m gpt-4.1 --json-output result.json
```

## Prompt Lint

```bash
oai-cli prompt-lint prompt.txt
cat prompt.txt | oai-cli prompt-lint --json
```

The linter is local-only and reports:

- score from `0` to `100`
- warnings
- suggestions
- improved prompt draft

It checks for vague wording, missing output format, missing constraints, conflicting instructions, overly long prompts, hidden requirements, possible secrets, and JSON requests without schema.

## JSON Mode

```bash
oai-cli json "Extract invoice fields" --schema schema.json
oai-cli json "Extract invoice fields" --schema schema.json --retry 2 --output result.json
oai-cli json "Show payload" --schema schema.json --dry-run
```

The command validates the schema locally, asks the model for JSON-only output, parses the response, and validates it against the schema before printing or writing it.

## Files

```bash
oai-cli files list
oai-cli files upload data.jsonl --purpose batch
oai-cli files retrieve file_...
oai-cli files delete file_...
oai-cli files download file_... --output out.bin
```

## Batch

```bash
oai-cli batch create requests.jsonl --endpoint /v1/responses --completion-window 24h
oai-cli batch create requests.jsonl --dry-run
oai-cli batch status batch_...
oai-cli batch list
oai-cli batch cancel batch_...
oai-cli batch download batch_... --output result.jsonl
```

`batch create` validates JSONL locally, shows row count, and previews the first row before upload.

## Models

```bash
oai-cli models list --refresh
oai-cli models cache
oai-cli models list
```

`models list` uses the local cache unless `--refresh` is passed or no cache exists.

## Eval

Create a JSONL file:

```jsonl
{"id":"case-1","prompt":"Summarize this in one sentence: ..."}
{"id":"case-2","prompt":"Extract the company name: ..."}
```

Run it:

```bash
oai-cli eval cases.jsonl -m gpt-4.1-mini -m gpt-4.1 --output eval-results.json
oai-cli eval cases.jsonl -m gpt-4.1-mini --dry-run
```

## Code Review

```bash
git diff | oai-cli code-review
git diff | oai-cli code-review --focus security --output json
git diff | oai-cli code-review --dry-run
```

Redaction is enabled before sending the diff.

## Explain Error

```bash
pytest 2>&1 | oai-cli explain-error
pytest 2>&1 | oai-cli explain-error --dry-run
```

Redaction is enabled before sending logs.

## Doctor

```bash
oai-cli doctor
oai-cli doctor --check-api
oai-cli doctor --json
```

Checks Python version, package version, SDK version, active profile, API key environment variable, base URL, config/log directories, and optionally a minimal API request.

## Exit Codes

- `0`: success
- `1`: general error
- `2`: config error
- `3`: API error
- `4`: validation error

## Security Notes

- API keys are read from environment variables.
- API key values are not printed in dry-run output.
- API keys are not stored in config by default.
- Redaction is enabled by default for sensitive workflows.
- If a key is pasted into a chat, issue, PR, terminal transcript, or committed file, revoke it and create a new one.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

ruff check openai_py_cli tests
pytest
mypy openai_py_cli
```
