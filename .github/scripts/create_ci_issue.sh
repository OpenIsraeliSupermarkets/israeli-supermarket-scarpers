#!/usr/bin/env bash
# Sync CI issues with the latest pytest log, one issue per test group.
#   - group = test class (e.g. KeshetTestCase), so a scraper's failures stay in one issue
#   - failing group: open an issue, or comment on / re-open the existing one
#   - passing group: comment and close its open issue
# Env: GH_TOKEN, GITHUB_WORKFLOW, GITHUB_REF, GITHUB_SHA, GITHUB_SERVER_URL,
#      GITHUB_REPOSITORY, GITHUB_RUN_ID
# Optional: CURSOR_MAINTAINER_WEBHOOK, CURSOR_WEBHOOK_SECRET (best effort, never fails the job)
# Args: <pytest-log-file>
set -euo pipefail

LOG_FILE="${1:-pytest-log.txt}"
RUN_URL="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
SHORT_SHA="${GITHUB_SHA:0:7}"
MAX_LEN=60000

[ -f "$LOG_FILE" ] || { echo "No pytest log; nothing to sync."; exit 0; }

# "<outcome> <test id>" pairs, de-duplicated (xdist prints each result twice).
RESULTS=$(grep -oE '(PASSED|FAILED|ERROR) [^ ]+::[^ ]+' "$LOG_FILE" | sort -u || true)

# test id -> group: the test class when present, else the file name.
group_of() {
  awk -F'::' '{ if (NF >= 3) print $2; else { n=split($1, p, "/"); print p[n] } }'
}

FAILED_IDS=$(printf '%s\n' "$RESULTS" | grep -E '^(FAILED|ERROR) ' | cut -d' ' -f2 || true)
FAILED_GROUPS=$(printf '%s\n' "$FAILED_IDS" | grep . | group_of | sort -u || true)
if [ -z "$FAILED_GROUPS" ] && grep -qE '^(FAILED|ERROR) ' "$LOG_FILE"; then
  FAILED_GROUPS="unknown"
fi
PASSED_GROUPS=$(
  printf '%s\n' "$RESULTS" | grep -E '^PASSED ' | cut -d' ' -f2 | group_of | sort -u \
    | { grep -vxFf <(printf '%s\n' "$FAILED_GROUPS") || true; }
)

gh label create automation -c "0E8A16" -d "Automation" 2>/dev/null || true
gh label create bug -c "d73a4a" -d "Bug" 2>/dev/null || true

marker_for() {
  local fp
  fp=$(printf 'workflow=%s|group=%s' "$GITHUB_WORKFLOW" "$1" | shasum -a 256 | cut -c1-12)
  printf '<!-- ci-fingerprint: %s -->' "$fp"
}

# find_issue <marker> <state> -> issue number (newest first)
find_issue() {
  gh issue list --state "$2" --label automation --limit 200 --json number,body \
    --jq ".[] | select(.body | contains(\"$1\")) | .number" | head -n 1
}

notify() {
  [ -n "${CURSOR_MAINTAINER_WEBHOOK:-}" ] || { echo "Webhook unset; skipped."; return 0; }
  local auth=()
  [ -z "${CURSOR_WEBHOOK_SECRET:-}" ] || auth=(-H "Authorization: Bearer ${CURSOR_WEBHOOK_SECRET}")
  local payload
  payload=$(jq -n --arg issue_url "$1" --arg run_url "$RUN_URL" --arg repo "$GITHUB_REPOSITORY" \
    --arg group "$2" --arg kind "ci-failure" \
    '{issue_url:$issue_url,run_url:$run_url,repo:$repo,group:$group,kind:$kind}')
  # Best effort: a bad webhook URL/secret must not fail the issue sync.
  if ! curl -sS --fail-with-body -X POST "$CURSOR_MAINTAINER_WEBHOOK" ${auth[@]+"${auth[@]}"} \
    -H "Content-Type: application/json" -d "$payload"; then
    echo "::warning::Maintainer webhook failed (check CURSOR_MAINTAINER_WEBHOOK / CURSOR_WEBHOOK_SECRET)."
  fi
}

for GROUP in $FAILED_GROUPS; do
  MARKER=$(marker_for "$GROUP")
  TESTS=$(printf '%s\n' "$FAILED_IDS" | grep . | while read -r id; do
    [ "$(printf '%s' "$id" | group_of)" = "$GROUP" ] && printf '%s\n' "$id"; done | sort -u || true)
  [ -n "$TESTS" ] || TESTS="unknown"

  OPEN=$(find_issue "$MARKER" open)
  if [ -n "$OPEN" ]; then
    gh issue comment "$OPEN" --body "Still failing: [run](${RUN_URL}) at ${SHORT_SHA}.

\`\`\`
${TESTS}
\`\`\`" || true
    continue
  fi

  CLOSED=$(find_issue "$MARKER" closed)
  if [ -n "$CLOSED" ]; then
    gh issue reopen "$CLOSED" || true
    gh issue comment "$CLOSED" --body "Failing again: [run](${RUN_URL}) at ${SHORT_SHA}.

\`\`\`
${TESTS}
\`\`\`" || true
    echo "Re-opened #${CLOSED} for ${GROUP}."
    notify "https://github.com/${GITHUB_REPOSITORY}/issues/${CLOSED}" "$GROUP"
    continue
  fi

  LOG_CONTENT=$(grep -F "$GROUP" "$LOG_FILE" | grep -vE '^\[gw[0-9]+\] \[ *[0-9]+%\] PASSED' | tail -c "$MAX_LEN" || true)
  BODY_FILE=$(mktemp)
  {
    echo "$MARKER"
    echo ""
    echo "**${GROUP}** failed in **${GITHUB_WORKFLOW}** on **${GITHUB_REF}** (${SHORT_SHA})."
    echo "This issue tracks the group's state: CI comments on every failing run and closes it when the group passes."
    echo ""
    echo "[View run](${RUN_URL})"
    echo ""
    echo "### Failed tests"
    echo ""
    echo '```'
    printf '%s\n' "$TESTS"
    echo '```'
    echo ""
    echo "### Pytest output (lines for ${GROUP})"
    echo ""
    echo '```'
    printf '%s\n' "$LOG_CONTENT"
    echo '```'
  } > "$BODY_FILE"
  ISSUE_URL=$(gh issue create --title "[CI] ${GITHUB_WORKFLOW}: ${GROUP}" \
    --body-file "$BODY_FILE" --label bug --label automation)
  echo "Created ${ISSUE_URL}"
  notify "$ISSUE_URL" "$GROUP"
done

for GROUP in $PASSED_GROUPS; do
  OPEN=$(find_issue "$(marker_for "$GROUP")" open)
  [ -n "$OPEN" ] || continue
  gh issue close "$OPEN" --comment "Passing again: [run](${RUN_URL}) at ${SHORT_SHA}. Closing; CI re-opens this issue if it fails again." \
    || true
  echo "Closed #${OPEN} for ${GROUP}."
done
