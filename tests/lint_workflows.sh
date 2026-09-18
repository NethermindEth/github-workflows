#!/usr/bin/env bash
#
# actionlint over the workflows in this repository.
#
# actionlint's value here is not style. It resolves ${{ }} expressions against the real
# context schema, so a typo in an input name is an error rather than an empty string at
# 03:00, and it runs shellcheck over every run: block, which is where a reusable workflow
# actually executes other people's data.
#
# The linter arrived after the workflows did, and five of them already had findings.
# Gating on a clean repository would have meant either leaving the linter off or editing
# five unrelated workflows in a change about something else. Instead they are exempted by
# name in tests/actionlint-legacy.txt, and that list can only shrink: a file listed there
# that now lints clean fails this script, so the exemption is removed by the commit that
# earns it rather than outliving the problem.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEGACY_LIST="${ROOT}/tests/actionlint-legacy.txt"

# Built once rather than invoked through `go run` per file: six `go run` calls is six
# link steps, and `go -C` would also leave every reported path relative to the tool's own
# module directory, which makes the findings harder to click than they need to be.
ACTIONLINT="$(mktemp -d)/actionlint"
go -C "${ROOT}/tools/actionlint" build -o "${ACTIONLINT}" github.com/rhysd/actionlint/cmd/actionlint

actionlint() {
  ( cd "${ROOT}" && "${ACTIONLINT}" -no-color -oneline "$@" )
}

is_legacy() {
  local candidate="$1" entry
  while IFS= read -r entry; do
    [[ "${entry}" == "${candidate}" ]] && return 0
  done < <(legacy_entries)
  return 1
}

legacy_entries() {
  sed -e 's/#.*//' -e 's/[[:space:]]*$//' "${LEGACY_LIST}" | grep -v '^$' || true
}

status=0

# Every entry must still name a real file, or a rename silently widens the exemption.
while IFS= read -r entry; do
  if [[ ! -f "${ROOT}/${entry}" ]]; then
    echo "::error::${LEGACY_LIST} lists ${entry}, which does not exist. Remove it."
    status=1
  fi
done < <(legacy_entries)

gated=()
while IFS= read -r workflow; do
  relative="${workflow#"${ROOT}/"}"
  if is_legacy "${relative}"; then
    continue
  fi
  gated+=("${relative}")
done < <(find "${ROOT}/.github/workflows" -maxdepth 1 -type f \( -name '*.yaml' -o -name '*.yml' \) | sort)

if (( ${#gated[@]} == 0 )); then
  echo "::error::no workflows left to lint, which means the exemption list swallowed all of them"
  exit 1
fi

echo "linting ${#gated[@]} workflow(s)"
if ! actionlint "${gated[@]}"; then
  status=1
fi

# The ratchet. A legacy file that now passes must leave the list.
while IFS= read -r entry; do
  [[ -f "${ROOT}/${entry}" ]] || continue
  if actionlint "${entry}" >/dev/null 2>&1; then
    echo "::error::${entry} now lints clean. Remove it from ${LEGACY_LIST}."
    status=1
  fi
done < <(legacy_entries)

if (( status == 0 )); then
  echo "workflows lint clean"
fi
exit "${status}"
