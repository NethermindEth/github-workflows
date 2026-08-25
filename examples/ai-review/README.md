# AI Review Workflow

Wraps the open-source [Qodo PR-Agent](https://github.com/the-pr-agent/pr-agent) action, routed
through the org LiteLLM gateway via Infisical, with a security gate and label. This is the same
pattern running in `citizen-automations` today.

## Setup

1. **Org secrets** on the consuming repo (or org-wide): `INFISICAL_IDENTITY_ID`,
   `INFISICAL_PROJECT_ID`.
2. **Infisical**: either use the shared gateway credential at `/apps/litellm/code-reviewer-prod`
   (key `LITELLM_API_KEY`, project `angkor-ai-platform`) by passing `secret_path:
   /apps/litellm/code-reviewer-prod`, or store your own `LLM_API_KEY` at
   `/github/workflows/<your-repo-name>` (the default `secret_path`) in the environment you pass
   as `env_slug` (default `prod`). The gateway API base is hardcoded in the workflow
   (`https://litellm.nethermind.dev/v1`), not read from Infisical, so `LLM_BASE_URL` isn't needed
   either way. `OPENAI.KEY` tries `LITELLM_API_KEY` then `LLM_API_KEY`, so either naming works.
3. **Label**: create a `needs-human-review` label on the repo (or pass a different `label` input).
4. Add the required status check in branch protection on your default branch. **The check name is
   `<your-job-id> / ai-review`, not `ai-review`** -- GitHub prefixes a reusable-workflow job's
   check with the CALLER's own job id. If you name your calling job `ai-review` (as in the example
   below), the actual check name is `ai-review / ai-review`. Getting this wrong means branch
   protection silently never enforces the gate -- verify the exact string in the PR's checks list
   before relying on it.

No `.pr_agent.toml` is required -- pass `model`, `fallback_model`, `extra_instructions`, and
`num_max_findings` as workflow inputs (see below). **Confirmed empirically (AUT-427): these env
vars win over a repo-local `.pr_agent.toml` for every key they both set** -- a toml is NOT a safe
way to override anything this workflow already covers (model, temperature, gateway routing,
review-requirement flags, suggestion thresholds, etc.), regardless of what PR-Agent's own docs
imply about local-config precedence. Use the four workflow inputs for those. A toml would only
have a chance of mattering for the (small) part of PR-Agent's config surface this workflow never
touches -- not something to rely on.

## Usage

`.github/workflows/ci.yml` (or your existing PR workflow):

```yaml
on:
  pull_request:
    branches: [main]

concurrency:
  group: ai-review-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  ai-review:
    uses: NethermindEth/github-workflows/.github/workflows/ai-review.yaml@stable
    with:
      extra_instructions: |
        Flag any hardcoded secret, PII sent to an external surface, or a publicly callable
        endpoint with no auth check as a security_concerns blocker; answer exactly "No" otherwise.
      num_max_findings: 8
    secrets:
      infisical_identity_id: ${{ secrets.INFISICAL_IDENTITY_ID }}
      infisical_project_id: ${{ secrets.INFISICAL_PROJECT_ID }}
```

`model`, `fallback_model`, `extra_instructions`, and `num_max_findings` all have sane defaults --
override only the ones you need.

The `concurrency` block above is **your responsibility to declare**, not the reusable workflow's:
concurrency groups are scoped per-repository, not per-workflow-file, so if the reusable workflow
declared its own group with the same name your caller uses, the two would collide and the job
could get cancelled before it's even scheduled (this is exactly the bug that hit citizen-automations
during migration -- see AUT-427). Pick a group name unique to your own workflow file/trigger.

Optional on-demand slash commands (`/review`, `/improve`, `/describe`, `/ask "..."` posted as a
PR comment), in a separate workflow file so a comment doesn't trigger your full CI suite:

`.github/workflows/ai-review-command.yaml`:

```yaml
on:
  issue_comment:
    types: [created]

# No cancel -- each comment is a distinct intent; without this, a burst of slash-commands runs
# in parallel and multiplies gateway spend.
concurrency:
  group: pr-agent-cmd-${{ github.event.issue.number }}
  cancel-in-progress: false

jobs:
  command:
    uses: NethermindEth/github-workflows/.github/workflows/ai-review-command.yaml@stable
    secrets:
      infisical_identity_id: ${{ secrets.INFISICAL_IDENTITY_ID }}
      infisical_project_id: ${{ secrets.INFISICAL_PROJECT_ID }}
```

## What it does and doesn't cover

- Blocks the `ai-review` check on an affirmative `security_concerns` finding from PR-Agent's
  `/review`, AND on any failure to produce a judgable review at all (LLM call error, gateway
  outage, malformed output). Everything else (bugs, /improve suggestions, the 0-100 score) is
  advisory. Fails **closed** in every case where something went wrong -- a broken pipeline should
  be visibly red, never silently green with just a label (this workflow used to fail open on a
  missing review; that let a fully broken model config pass CI for a while before anyone noticed,
  see AUT-427). `CONFIG.PROPAGATE_TOOL_ERRORS` is set so PR-Agent's own step fails loudly on an
  LLM error instead of swallowing it and exiting 0 with nothing to show. A real `security_concerns`
  finding always blocks; the "no judgable review" half of that can be relaxed to advisory-only
  per caller via `fail_on_missing_review: false` (default `true`), for riding out a known gateway
  outage without forking the workflow.
- Skips entirely for `dependabot[bot]` (no Infisical creds on those runs) -- your own
  deterministic CI checks are what gates dependency-bump PRs, not this workflow.
- Never runs on fork PRs (no secrets, no gate there).
- This does **not** include citizen-automations' own deterministic domain gate
  (REVIEW.md / metadata.yaml truthfulness checks) -- that logic is specific to their
  citizen-developer monorepo conventions and isn't part of this reusable workflow.
