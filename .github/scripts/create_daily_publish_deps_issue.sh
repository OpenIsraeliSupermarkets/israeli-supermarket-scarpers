#!/usr/bin/env bash
# Open a deduped dependency-bump issue on daily-publish after a library release.
# Env:
#   GH_TOKEN                 — issues:write on daily-publish
#   PACKAGE_NAME             — PyPI package name (il-supermarket-scraper | il-supermarket-parser)
#   PACKAGE_VERSION          — semver without leading v
#   RELEASE_TAG              — e.g. v1.0.4
#   RELEASE_URL              — GitHub release URL
#   SOURCE_REPO              — owner/repo that released (optional, for body)
#   DAILY_PUBLISH_REPO       — default OpenIsraeliSupermarkets/daily-publish-supermarket-data
set -euo pipefail

DAILY_PUBLISH_REPO="${DAILY_PUBLISH_REPO:-OpenIsraeliSupermarkets/daily-publish-supermarket-data}"
PACKAGE_NAME="${PACKAGE_NAME:?}"
PACKAGE_VERSION="${PACKAGE_VERSION:?}"
RELEASE_TAG="${RELEASE_TAG:?}"
RELEASE_URL="${RELEASE_URL:?}"
SOURCE_REPO="${SOURCE_REPO:-}"

FP_SRC="kind=deps-bump|package=${PACKAGE_NAME}|version=${PACKAGE_VERSION}"
FP=$(printf '%s' "$FP_SRC" | shasum -a 256 | cut -c1-12)
MARKER="<!-- ci-fingerprint: ${FP} -->"

EXISTING=$(
  gh issue list --repo "${DAILY_PUBLISH_REPO}" --state open --label automation --json number,body \
    --jq ".[] | select(.body | contains(\"${MARKER}\")) | .number" \
    | head -n 1
)

if [ -n "${EXISTING}" ]; then
  echo "Open daily-publish issue #${EXISTING} already covers ${PACKAGE_NAME}==${PACKAGE_VERSION}; skipping."
  gh issue comment --repo "${DAILY_PUBLISH_REPO}" "${EXISTING}" \
    --body "Recurrence: ${RELEASE_TAG} — ${RELEASE_URL}" || true
  exit 0
fi

gh label create automation --repo "${DAILY_PUBLISH_REPO}" -c "0E8A16" -d "Automation" 2>/dev/null || true
gh label create dependencies --repo "${DAILY_PUBLISH_REPO}" -c "0366d6" -d "Dependency update" 2>/dev/null || true

LABEL_ARGS=(--label automation)
if gh label list --repo "${DAILY_PUBLISH_REPO}" --json name --jq '.[].name' | grep -qx dependencies; then
  LABEL_ARGS+=(--label dependencies)
fi

BODY_FILE=$(mktemp)
{
  echo "${MARKER}"
  echo ""
  echo "**${PACKAGE_NAME}** released **${RELEASE_TAG}** (\`${PACKAGE_NAME}>=${PACKAGE_VERSION}\`)."
  echo ""
  echo "Release: ${RELEASE_URL}"
  if [ -n "${SOURCE_REPO}" ]; then
    echo "Source: https://github.com/${SOURCE_REPO}"
  fi
  echo ""
  echo "### Update checklist"
  echo ""
  echo "- [ ] Bump \`${PACKAGE_NAME}>=${PACKAGE_VERSION}\` in \`requirements.txt\`"
  echo "- [ ] Open a PR (or push) so System Test on PR to Main can run"
  echo "- [ ] Merge when green"
} > "$BODY_FILE"

ISSUE_URL=$(
  gh issue create --repo "${DAILY_PUBLISH_REPO}" \
    --title "[deps] Bump ${PACKAGE_NAME} to ${PACKAGE_VERSION}" \
    --body-file "$BODY_FILE" \
    "${LABEL_ARGS[@]}"
)
echo "Created ${ISSUE_URL}"
