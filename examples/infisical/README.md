# Infisical Secrets Examples

Examples for using the `get_infisical_secrets` composite action to load secrets from Infisical
into your GitHub Actions workflows via OIDC authentication.

## Prerequisites

1. Your repository must have these secrets set:
   - `INFISICAL_IDENTITY_ID` — the Infisical machine identity ID (managed by Terraform)
   - `INFISICAL_PROJECT_ID` — the Infisical project ID (managed by Terraform)

2. Your workflow must declare `permissions: id-token: write` for OIDC authentication.

3. Your secrets must exist in Infisical at `/github/workflows/<repo-name>` (or a custom path).

## Examples

| Example | Description |
|---|---|
| [load-secrets-env.yml](load-secrets-env.yml) | Load secrets as environment variables (default) |
| [load-secrets-custom-path.yml](load-secrets-custom-path.yml) | Load secrets from a custom Infisical path |
| [load-secrets-file.yml](load-secrets-file.yml) | Write secrets to a `.env` file |
| [load-secrets-multiple-envs.yml](load-secrets-multiple-envs.yml) | Load different secrets per branch/environment |

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `identity-id` | yes | — | Infisical machine identity ID |
| `project-id` | yes | — | Infisical project ID |
| `env-slug` | yes | — | Environment slug (`dev`, `staging`, `prod`) |
| `export-type` | no | `env` | `env` (environment variables) or `file` (.env file) |
| `file-path` | no | `.env` | Output file path (only for `export-type: file`) |
| `secret-path` | no | `/github/workflows/<repo-name>` | Override the secret path |
| `domain` | no | `https://app.infisical.com` | Infisical instance URL |
