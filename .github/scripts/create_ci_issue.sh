#!/usr/bin/env bash
# Create a deduped CI failure issue and webhook the maintainer when new.
# Env: GITHUB_TOKEN, GITHUB_WORKFLOW, GITHUB_REF, GITHUB_SHA, GITHUB_SERVER_URL,
#      GITHUB_REPOSITORY, GITHUB_RUN_ID
# Optional: CURSOR_MAINTAINER_WEBHOOK, CURSOR_WEBHOOK_SECRET
# Args: <pytest-log-file>
set -euo pipefail

LOG_FILE="${1:-pytest-log.txt}"
RUN_URL="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"

FAILURES=$(
  if [ -f "$LOG_FILE" ]; then
    { grep -E '^FAILED ' "$LOG_FILE" || grep -E '^ERROR ' "$LOG_FILE" || true; } \
      | sed -E 's/^(FAILED|ERROR) //' | sed -E 's/ .*$//' | sort -u | head -n 20
  fi
)
if [ -z "${FAILURES}" ]; then
  FAILURES="unknown"
fi
FAILURE_CSV=$(printf '%s\n' "$FAILURES" | paste -sd, -)
FP_SRC="workflow=${GITHUB_WORKFLOW}|failures=${FAILURE_CSV}"
FP=$(printf '%s' "$FP_SRC" | shasum -a 256 | cut -c1-12)
MARKER="<!-- ci-fingerprint: ${FP} -->"

EXISTING=$(
  gh issue list --state open --label automation --json number,body \
    --jq ".[] | select(.body | contains(\"${MARKER}\")) | .number" \
    | head -n 1
)

if [ -n "${EXISTING}" ]; then
  echo "Open issue #${EXISTING} already covers fingerprint ${FP}; skipping create/webhook."
  gh issue comment "${EXISTING}" --body "Recurrence: [run](${RUN_URL}) at ${GITHUB_SHA:0:7}." || true
  exit 0
fi

FIRST=$(printf '%s\n' "$FAILURES" | head -n 1)
TITLE_SUFFIX="$FIRST"
if [ "$(printf '%s\n' "$FAILURES" | wc -l | tr -d ' ')" -gt 1 ]; then
  TITLE_SUFFIX="multiple failures"
fi
TITLE="[CI] ${GITHUB_WORKFLOW}: ${TITLE_SUFFIX}"

MAX_LEN=60000
if [ -f "$LOG_FILE" ]; then
  LOG_CONTENT=$(cat "$LOG_FILE")
  LEN=${#LOG_CONTENT}
  if [ "$LEN" -gt "$MAX_LEN" ]; then
    LOG_CONTENT="…(truncated)"$'\n\n'"${LOG_CONTENT: -$MAX_LEN}"
  fi
else
  LOG_CONTENT="(pytest log not found)"
fi

BODY_FILE=$(mktemp)
{
  echo "${MARKER}"
  echo ""
  echo "Workflow **${GITHUB_WORKFLOW}** failed on **${GITHUB_REF}** (${GITHUB_SHA:0:7})."
  echo ""
  echo "[View run](${RUN_URL})"
  echo ""
  echo "### Failed tests"
  echo ""
  echo '```'
  printf '%s\n' "$FAILURES"
  echo '```'
  echo ""
  echo "### Pytest output"
  echo ""
  echo '```'
  printf '%s\n' "$LOG_CONTENT"
  echo '```'
} > "$BODY_FILE"

gh label create automation -c "0E8A16" -d "Automation" 2>/dev/null || true
gh label create bug -c "d73a4a" -d "Bug" 2>/dev/null || true

ISSUE_URL=$(
  gh issue create \
    --title "$TITLE" \
    --body-file "$BODY_FILE" \
    --label "bug" \
    --label "automation"
)
echo "Created ${ISSUE_URL}"

if [ -n "${CURSOR_MAINTAINER_WEBHOOK:-}" ]; then
  AUTH_HEADER=()
  if [ -n "${CURSOR_WEBHOOK_SECRET:-}" ]; then
    AUTH_HEADER=(-H "Authorization: Bearer ${CURSOR_WEBHOOK_SECRET}")
  fi
  curl -fsS -X POST "${CURSOR_MAINTAINER_WEBHOOK}" \
    "${AUTH_HEADER[@]}" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
      --arg issue_url "$ISSUE_URL" \
      --arg run_url "$RUN_URL" \
      --arg repo "$GITHUB_REPOSITORY" \
      --arg fingerprint "$FP" \
      --arg kind "ci-failure" \
      '{issue_url:$issue_url,run_url:$run_url,repo:$repo,fingerprint:$fingerprint,kind:$kind}')"
  echo "Webhook posted."
else
  echo "CURSOR_MAINTAINER_WEBHOOK unset; skipped webhook."
fi
