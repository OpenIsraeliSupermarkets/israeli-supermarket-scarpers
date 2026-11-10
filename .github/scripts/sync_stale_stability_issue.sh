#!/usr/bin/env bash
# Weekly: report ScraperStability rules that approved "no files" while the
# scraper returned files (STALE_STABILITY_RULE warnings in the scheduled
# test-suite pytest logs). Keeps ONE issue, found by its fingerprint marker:
#   - findings, no open issue: open one (re-open a closed one)
#   - findings, open issue: refresh its body and comment with this week's table
#   - no findings: close the open issue
# Env: GH_TOKEN, GITHUB_REPOSITORY, GITHUB_SERVER_URL, GITHUB_RUN_ID
# Optional: DAYS (default 7), TEST_WORKFLOW (default test-suite.yml)
set -euo pipefail

DAYS="${DAYS:-7}"
TEST_WORKFLOW="${TEST_WORKFLOW:-test-suite.yml}"
RUN_URL="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
SINCE=$(date -u -d "-${DAYS} days" +%Y-%m-%d)
WORK=$(mktemp -d)
mkdir -p "$WORK/logs"

gh run list --workflow "$TEST_WORKFLOW" --event schedule --created ">=${SINCE}" \
  --limit 100 --json databaseId,createdAt,url,status \
  --jq '[.[] | select(.status == "completed")]' > "$WORK/runs.json"
echo "Scheduled ${TEST_WORKFLOW} runs since ${SINCE}: $(jq length "$WORK/runs.json")"

for id in $(jq -r '.[].databaseId' "$WORK/runs.json"); do
  gh run download "$id" -n pytest-log -D "$WORK/logs/$id" >/dev/null 2>&1 \
    || echo "No pytest-log artifact for run ${id}; skipped."
done

COUNT=$(python -m scripts.stale_stability_report --runs "$WORK/runs.json" \
  --logs-dir "$WORK/logs" --out "$WORK/table.md" --since "$SINCE")
echo "Stale-looking rules: ${COUNT}"

gh label create automation -c "0E8A16" -d "Automation" 2>/dev/null || true
gh label create stability -c "FBCA04" -d "ScraperStability rules" 2>/dev/null || true

FP=$(printf 'kind=stale-stability-rules|repo=%s' "$GITHUB_REPOSITORY" | shasum -a 256 | cut -c1-12)
MARKER="<!-- ci-fingerprint: ${FP} -->"

find_issue() {
  gh issue list --state "$1" --label automation --limit 200 --json number,body \
    --jq ".[] | select(.body | contains(\"${MARKER}\")) | .number" | head -n 1
}

OPEN=$(find_issue open)

if [ "$COUNT" = "0" ]; then
  if [ -n "$OPEN" ]; then
    gh issue close "$OPEN" --comment "No stale-looking stability rules since ${SINCE} ([report run](${RUN_URL})). Closing; the weekly report re-opens this if warnings come back." || true
    echo "Closed #${OPEN}."
  fi
  exit 0
fi

BODY_FILE="$WORK/body.md"
{
  echo "$MARKER"
  echo ""
  echo "Updated weekly by **stale-stability-rules** ([latest run](${RUN_URL}))."
  echo ""
  cat "$WORK/table.md"
} > "$BODY_FILE"

if [ -z "$OPEN" ]; then
  CLOSED=$(find_issue closed)
  if [ -n "$CLOSED" ]; then
    gh issue reopen "$CLOSED"
    OPEN="$CLOSED"
  fi
fi

if [ -n "$OPEN" ]; then
  gh issue edit "$OPEN" --body-file "$BODY_FILE"
  gh issue comment "$OPEN" --body-file "$WORK/table.md" || true
  echo "Updated #${OPEN}."
else
  URL=$(gh issue create --title "[stability] Rules that approved \"no files\" but files were found" \
    --body-file "$BODY_FILE" --label automation --label stability)
  echo "Created ${URL}"
fi
