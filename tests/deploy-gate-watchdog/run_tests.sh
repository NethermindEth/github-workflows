#!/usr/bin/env bash
#
# Tests for the deploy gate watchdog. Runs the step body extracted from the workflow
# itself (see extract_step.py) against a stubbed gh CLI.
#
# Exit codes are the contract under test: 0 shipped or inside the grace window, 1 stale,
# 2 bad arguments. Asserting only "non-zero" would let a validation bug pass as a
# successful detection, which is the one confusion a watchdog cannot afford.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
WORKFLOW="${ROOT}/.github/workflows/actions-watchdog-deploy-gate.yaml"

STEP_SCRIPT="$(mktemp)"
if ! python3 "${HERE}/extract_step.py" "${WORKFLOW}" watchdog check > "${STEP_SCRIPT}"; then
  echo "could not extract the watchdog step from ${WORKFLOW}" >&2
  exit 1
fi
if [[ ! -s "${STEP_SCRIPT}" ]]; then
  echo "extracted an empty step body from ${WORKFLOW}" >&2
  exit 1
fi

failures=0
current_case=""

minutes_ago() {
  python3 -c 'import datetime, sys; print((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=int(sys.argv[1]))).strftime("%Y-%m-%dT%H:%M:%SZ"))' "$1"
}

# head_at AGE_MINUTES SHA -> the commit payload the watchdog reads for the branch head.
head_at() {
  printf '{"sha":"%s","commit":{"committer":{"date":"%s"}}}\n' "$2" "$(minutes_ago "$1")"
}

runs_with() {
  if [[ -z "${1}" ]]; then
    printf '{"workflow_runs":[]}\n'
  else
    printf '{"workflow_runs":[{"head_sha":"%s","status":"completed","conclusion":"%s","html_url":"https://example.invalid/run/1"}]}\n' "$1" "${2:-success}"
  fi
}

begin_case() {
  current_case="$1"
  STUB="$(mktemp -d)"
  export STUB
  mkdir -p "${STUB}/bin"
  cp "${HERE}/stub-gh" "${STUB}/bin/gh"
  chmod +x "${STUB}/bin/gh"
  : > "${STUB}/calls.log"
  : > "${STUB}/bodies.log"
  : > "${STUB}/reported.txt"
  : > "${STUB}/issue_number.txt"
  runs_with "" > "${STUB}/head_run.json"
}

# run_watchdog [VAR=VALUE ...] -> exit status in $status, stdout+stderr in $output.
run_watchdog() {
  local out
  out="$(
    PATH="${STUB}/bin:${PATH}" \
    GH_TOKEN=stub-token \
    REPO="acme/widget" \
    RUN_URL="https://example.invalid/watchdog" \
    GITHUB_STEP_SUMMARY="${STUB}/summary.md" \
    INPUT_WORKFLOW_FILE="${INPUT_WORKFLOW_FILE-build-images.yaml}" \
    INPUT_BRANCH="${INPUT_BRANCH-main}" \
    INPUT_GRACE_MINUTES="${INPUT_GRACE_MINUTES-90}" \
    INPUT_ISSUE_LABEL="${INPUT_ISSUE_LABEL-deploy-gate-stale}" \
    INPUT_ISSUE_ASSIGNEES="${INPUT_ISSUE_ASSIGNEES-}" \
    bash "${STEP_SCRIPT}" 2>&1
  )"
  status=$?
  output="${out}"
}

fail() {
  echo "  FAIL ${current_case}: $1"
  [[ -n "${2:-}" ]] && echo "       ${2}"
  failures=$((failures + 1))
}

pass() { echo "  ok   ${current_case}"; }

expect_status() {
  if [[ "${status}" -ne "$1" ]]; then
    fail "expected exit ${1}, got ${status}" "${output}"
    return 1
  fi
  return 0
}

expect_calls() {
  if ! grep -qF -- "$1" "${STUB}/calls.log"; then
    fail "expected gh to be called with: $1" "$(cat "${STUB}/calls.log")"
    return 1
  fi
  return 0
}

expect_no_calls() {
  if grep -qF -- "$1" "${STUB}/calls.log"; then
    fail "expected gh NOT to be called with: $1" "$(cat "${STUB}/calls.log")"
    return 1
  fi
  return 0
}

expect_body() {
  if ! grep -qF -- "$1" "${STUB}/bodies.log"; then
    fail "expected the published body to contain: $1" "$(cat "${STUB}/bodies.log")"
    return 1
  fi
  return 0
}

expect_output() {
  if ! grep -qF -- "$1" <<< "${output}"; then
    fail "expected output to contain: $1" "${output}"
    return 1
  fi
  return 0
}

readonly HEAD_SHA=1111111111111111111111111111111111111111
readonly OLD_SHA=2222222222222222222222222222222222222222

# --- shipped ----------------------------------------------------------------------

begin_case "head is shipped: succeeds and touches no issue"
head_at 5 "${HEAD_SHA}" > "${STUB}/head.json"
runs_with "${HEAD_SHA}" > "${STUB}/last_ok.json"
run_watchdog
expect_status 0 && expect_no_calls "[issue][create]" && expect_no_calls "[issue][comment]" && pass

begin_case "head is shipped with an issue open: comments and closes it"
head_at 5 "${HEAD_SHA}" > "${STUB}/head.json"
runs_with "${HEAD_SHA}" > "${STUB}/last_ok.json"
echo "42" > "${STUB}/issue_number.txt"
run_watchdog
expect_status 0 && expect_calls "[issue][comment][42]" && expect_calls "[issue][close][42]" &&
  expect_body "Recovered." && pass

# --- unshipped but young ----------------------------------------------------------

begin_case "head is younger than the grace window: succeeds quietly"
head_at 10 "${HEAD_SHA}" > "${STUB}/head.json"
runs_with "${OLD_SHA}" > "${STUB}/last_ok.json"
run_watchdog
expect_status 0 && expect_no_calls "[issue][create]" && expect_no_calls "[issue][comment]" &&
  expect_output "inside the 90m grace window" && pass

begin_case "grace window of zero reports a brand new commit immediately"
head_at 0 "${HEAD_SHA}" > "${STUB}/head.json"
runs_with "${OLD_SHA}" > "${STUB}/last_ok.json"
INPUT_GRACE_MINUTES=0 run_watchdog
expect_status 1 && expect_calls "[issue][create]" && pass

# --- stale ------------------------------------------------------------------------

begin_case "head is stale: fails and opens one issue"
head_at 500 "${HEAD_SHA}" > "${STUB}/head.json"
runs_with "${OLD_SHA}" > "${STUB}/last_ok.json"
runs_with "${HEAD_SHA}" failure > "${STUB}/head_run.json"
run_watchdog
expect_status 1 && expect_calls "[issue][create]" && expect_body "${HEAD_SHA}" &&
  expect_body "completed / failure" && pass

begin_case "gate never ran for the head: still stale, and says so"
head_at 500 "${HEAD_SHA}" > "${STUB}/head.json"
runs_with "" > "${STUB}/last_ok.json"
runs_with "" > "${STUB}/head_run.json"
run_watchdog
expect_status 1 && expect_calls "[issue][create]" && expect_body "never ran / none" &&
  expect_body "none on record" && pass

begin_case "stale with an issue that predates this commit: comments"
head_at 500 "${HEAD_SHA}" > "${STUB}/head.json"
runs_with "${OLD_SHA}" > "${STUB}/last_ok.json"
echo "7" > "${STUB}/issue_number.txt"
echo "an older report about ${OLD_SHA}" > "${STUB}/reported.txt"
run_watchdog
expect_status 1 && expect_calls "[issue][comment][7]" && expect_no_calls "[issue][create]" && pass

begin_case "stale with this commit already reported: stays quiet but still fails"
head_at 500 "${HEAD_SHA}" > "${STUB}/head.json"
runs_with "${OLD_SHA}" > "${STUB}/last_ok.json"
echo "7" > "${STUB}/issue_number.txt"
echo "already reported ${HEAD_SHA} here" > "${STUB}/reported.txt"
run_watchdog
expect_status 1 && expect_no_calls "[issue][comment]" && expect_no_calls "[issue][create]" &&
  expect_output "already reports" && pass

begin_case "assignees are passed through when set"
head_at 500 "${HEAD_SHA}" > "${STUB}/head.json"
runs_with "${OLD_SHA}" > "${STUB}/last_ok.json"
INPUT_ISSUE_ASSIGNEES="octocat,hubot" run_watchdog
expect_status 1 && expect_calls "[--assignee][octocat,hubot]" && pass

# --- rejected input ---------------------------------------------------------------
#
# Each of these asserts the specific rejection, not just exit 2: a message naming the
# wrong input is the difference between a useful failure and a mystery.

begin_case "workflow_file with a path traversal is rejected"
INPUT_WORKFLOW_FILE="../../../etc/passwd.yaml" run_watchdog
expect_status 2 && expect_output "workflow_file must be a workflow file name" &&
  expect_no_calls "[api]" && pass

begin_case "workflow_file with a query separator is rejected"
INPUT_WORKFLOW_FILE="build.yaml?status=success" run_watchdog
expect_status 2 && expect_output "workflow_file must be a workflow file name" && pass

begin_case "workflow_file without a yaml extension is rejected"
INPUT_WORKFLOW_FILE="build-images" run_watchdog
expect_status 2 && expect_output "workflow_file must be a workflow file name" && pass

begin_case "branch with a shell metacharacter is rejected"
INPUT_BRANCH='main;id' run_watchdog
expect_status 2 && expect_output "branch must be a plain branch name" && pass

begin_case "branch with a query separator is rejected"
INPUT_BRANCH='main&per_page=100' run_watchdog
expect_status 2 && expect_output "branch must be a plain branch name" && pass

begin_case "non-numeric grace_minutes is rejected"
INPUT_GRACE_MINUTES="soon" run_watchdog
expect_status 2 && expect_output "grace_minutes must be a non-negative integer" && pass

begin_case "negative grace_minutes is rejected"
INPUT_GRACE_MINUTES="-5" run_watchdog
expect_status 2 && expect_output "grace_minutes must be a non-negative integer" && pass

begin_case "issue_label with an illegal character is rejected"
INPUT_ISSUE_LABEL='bad!label' run_watchdog
expect_status 2 && expect_output "issue_label must be 1-49 characters" && pass

begin_case "empty issue_label is rejected"
INPUT_ISSUE_LABEL='' run_watchdog
expect_status 2 && expect_output "issue_label must be 1-49 characters" && pass

begin_case "issue_assignees with a shell metacharacter is rejected"
INPUT_ISSUE_ASSIGNEES='octocat;id' run_watchdog
expect_status 2 && expect_output "issue_assignees must be comma-separated" && pass

# ----------------------------------------------------------------------------------

echo
if (( failures > 0 )); then
  echo "${failures} failing case(s)"
  exit 1
fi
echo "all cases passed"
