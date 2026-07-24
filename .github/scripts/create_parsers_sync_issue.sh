#!/usr/bin/env bash
# Open a deduped scraper-sync issue on the parsers repo and webhook the parsers maintainer.
# Env: GH_TOKEN (or GITHUB_TOKEN) with issues:write on parsers,
#      SCRAPER_VERSION, RELEASE_TAG, RELEASE_URL,
#      PARSERS_REPO (default OpenIsraeliSupermarkets/israeli-supermarket-parsers),
#      Optional CURSOR_MAINTAINER_WEBHOOK, CURSOR_WEBHOOK_SECRET (parsers maintainer webhook)
set -euo pipefail

PARSERS_REPO="${PARSERS_REPO:-OpenIsraeliSupermarkets/israeli-supermarket-parsers}"
SCRAPER_VERSION="${SCRAPER_VERSION:?}"
RELEASE_TAG="${RELEASE_TAG:?}"
RELEASE_URL="${RELEASE_URL:?}"

FP_SRC="kind=scraper-sync|scraper_version=${SCRAPER_VERSION}"
FP=$(printf '%s' "$FP_SRC" | shasum -a 256 | cut -c1-12)
MARKER="<!-- ci-fingerprint: ${FP} -->"

EXISTING=$(
  gh issue list --repo "${PARSERS_REPO}" --state open --label automation --json number,body \
    --jq ".[] | select(.body | contains(\"${MARKER}\")) | .number" \
    | head -n 1
)

if [ -n "${EXISTING}" ]; then
  echo "Open parsers issue #${EXISTING} already covers sync ${SCRAPER_VERSION}; skipping."
  gh issue comment --repo "${PARSERS_REPO}" "${EXISTING}" \
    --body "Recurrence: scrapers ${RELEASE_TAG} — ${RELEASE_URL}" || true
  exit 0
fi

BODY_FILE=$(mktemp)
{
  echo "${MARKER}"
  echo ""
  echo "Scrapers published **${RELEASE_TAG}** (\`il-supermarket-scraper==${SCRAPER_VERSION}\`)."
  echo ""
  echo "Release: ${RELEASE_URL}"
  echo ""
  echo "### Maintainer checklist"
  echo ""
  echo "- [ ] Bump \`il-supermarket-scraper>=${SCRAPER_VERSION}\` in \`requirements.txt\` if needed"
  echo "- [ ] Mirror \`ScraperFactory\` → \`ParserFactory\` + \`test_all.py\`"
  echo "- [ ] Run Docker pytest / pylint"
  echo "- [ ] If changes needed: bump parsers \`setup.py\` and create a release"
  echo "- [ ] If no changes needed: comment **no need new version** and close"
} > "$BODY_FILE"

gh label create automation -c "0E8A16" -d "Automation" 2>/dev/null || true
gh label create sync -c "1D76DB" -d "Upstream sync" 2>/dev/null || true

# sync label may not exist; create issue with automation (+ sync if present)
LABEL_ARGS=(--label automation)
if gh label list --repo "${PARSERS_REPO}" --json name --jq '.[].name' | grep -qx sync; then
  LABEL_ARGS+=(--label sync)
fi

ISSUE_URL=$(
  gh issue create --repo "${PARSERS_REPO}" \
    --title "[sync] il-supermarket-scraper v${SCRAPER_VERSION}" \
    --body-file "$BODY_FILE" \
    "${LABEL_ARGS[@]}"
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
      --arg release_url "$RELEASE_URL" \
      --arg repo "$PARSERS_REPO" \
      --arg fingerprint "$FP" \
      --arg kind "scraper-sync" \
      --arg scraper_version "$SCRAPER_VERSION" \
      '{issue_url:$issue_url,release_url:$release_url,repo:$repo,fingerprint:$fingerprint,kind:$kind,scraper_version:$scraper_version}')"
  echo "Webhook posted."
else
  echo "CURSOR_MAINTAINER_WEBHOOK unset; skipped webhook."
fi
