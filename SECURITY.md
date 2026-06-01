# Security Policy

## Secrets

Do not commit API keys, CSV exports with keys, local `.env` files, SQLite logs, or raw production logs.

If a key is pasted into an issue, PR, chat, terminal transcript, or committed file, treat it as compromised:

1. Revoke it in the provider dashboard.
2. Create a new key.
3. Export it through an environment variable such as `OPENAI_API_KEY`.

`oai-cli` stores the name of the environment variable by default, not the key value.

## Reporting

Open a private security advisory when available, or contact the maintainers without including live secrets.
