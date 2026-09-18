# Deploy Gate Watchdog

**Implementation:** [`.github/workflows/actions-watchdog-deploy-gate.yaml`](../../.github/workflows/actions-watchdog-deploy-gate.yaml)

**Example:** [`examples/watchdog/deploy-gate-watchdog.yml`](./deploy-gate-watchdog.yml)

## The failure this exists for

A build-and-push workflow is a deploy gate: when it succeeds an image lands in the
registry and the deployer picks it up, and when it fails nothing lands and the deployer
has nothing new to sync. That second case is silent. Production keeps serving the last
image that made it through, the branch still looks merged and green in the PR list, and
the only signal is a grey cross on a commit page nobody opens.

It happened on `angkor-platform-frontend`: the Trivy stage of the build started failing
before the push step, main went unshipped for days, and production stayed on an image
with known auth-bypass CVEs. It surfaced only because someone shipped an unrelated fix
and noticed it never appeared.

This workflow asks, on a schedule, the question that was never being asked: **is the head
of the release branch represented by a successful run of the gate?** If not, it opens one
issue and fails. When the branch ships again it closes the issue by itself.

It is deliberately a watchdog and not an on-failure notification. A failure hook is a
strictly weaker signal — it can only fire when the gate ran and lost. It cannot fire when
the gate never ran at all: workflow disabled, trigger deleted or path-filtered away,
runner outage, a schedule that stopped. Those are the failures that stay hidden longest,
and they are the ones a watchdog catches for free.

## Usage

Copy [`deploy-gate-watchdog.yml`](./deploy-gate-watchdog.yml) into `.github/workflows/`
and set `workflow_file` to the workflow that publishes your artifact.

The caller must grant `actions: read` (to read run history) and `issues: write` (to file
the alert). No secrets, no webhooks: it runs on the built-in `GITHUB_TOKEN`.

## Inputs

| Input | Default | Notes |
|---|---|---|
| `workflow_file` | *required* | File name of the gating workflow, e.g. `build-images.yaml`. The file name and not the display name, so renaming the workflow's `name:` cannot silently detach the watchdog. |
| `branch` | `main` | Branch whose head must be shipped. |
| `grace_minutes` | `90` | How long a commit may go unshipped before it counts as stale. Must comfortably exceed an end-to-end run of the gate, or every push trips the watchdog while it is still building. |
| `issue_label` | `deploy-gate-stale` | Used to find and deduplicate the issue. One open issue per label. |
| `issue_assignees` | *(none)* | Comma-separated usernames to assign the issue to. |

Every input is validated against an allowlist before any API call, and a rejected input
fails the run rather than being cleaned up and used.

## Behaviour

| Situation | Result |
|---|---|
| Branch head has a successful gate run | Succeeds. Closes the watchdog's issue if one is open. |
| Branch head unshipped, younger than `grace_minutes` | Succeeds quietly. The build is presumed to still be running. |
| Branch head unshipped and older than `grace_minutes` | Fails, and opens an issue naming the head, its age, and what the gate did for that commit. |
| Same head still stale on the next run | Fails, comments nothing. An hourly comment about one unchanged commit is how an issue gets muted. |
| A newer head is also stale | Fails, and comments on the existing issue with the new head. |

Exit codes are distinct on purpose: `0` shipped or within grace, `1` stale, `2` called
with arguments it cannot act on.

## Choosing `grace_minutes`

Set it above the p95 wall-clock time of the gate, measured rather than guessed, and leave
room for queueing. Too low and the watchdog files an issue against a build that was going
to succeed five minutes later, which is the fastest way to teach people to ignore it. Too
high and a genuinely broken main stays quiet for that long. The 90 minute default suits a
multi-arch image build with a scan stage.

## Tests

`tests/deploy-gate-watchdog/run_tests.sh`, runnable locally with nothing but bash and
python3. The suite runs the step body extracted from the workflow file itself against a
stubbed `gh`, so there is one copy of the logic and the tests are pinned to the text that
actually ships.
