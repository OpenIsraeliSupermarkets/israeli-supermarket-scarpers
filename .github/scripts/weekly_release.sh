#!/usr/bin/env bash
# Change-gate weekly release: noop if no commits since last v* tag; else bump setup.py patch, tag, release.
# Env: GITHUB_TOKEN (contents write), GITHUB_REPOSITORY
# Outputs via GITHUB_OUTPUT when present: outcome=noop|released, version=...
set -euo pipefail

if [ "${GITHUB_REF_NAME:-}" != "main" ]; then
  echo "Refusing to run weekly release outside main (got: ${GITHUB_REF_NAME:-unset}). This script pushes directly to main; only run it from main." >&2
  exit 1
fi

git fetch --tags --force origin
LATEST_TAG=$(git tag -l 'v*' --sort=-v:refname | head -n 1 || true)
if [ -z "${LATEST_TAG}" ]; then
  echo "No existing v* tags; treating all history as candidates."
  COMMIT_COUNT=$(git rev-list --count HEAD)
else
  COMMIT_COUNT=$(git rev-list --count "${LATEST_TAG}..HEAD")
fi
echo "Latest tag: ${LATEST_TAG:-<none>}; commits since: ${COMMIT_COUNT}"

if [ "${COMMIT_COUNT}" -eq 0 ]; then
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "outcome=noop" >> "$GITHUB_OUTPUT"
  fi
  echo "No commits since last tag; noop."
  exit 0
fi

CURRENT=$(python - <<'PY'
import re, pathlib
text = pathlib.Path("setup.py").read_text(encoding="utf-8")
m = re.search(r'version\s*=\s*"([^"]+)"', text)
if not m:
    raise SystemExit("version= not found in setup.py")
print(m.group(1))
PY
)
IFS=. read -r MAJOR MINOR PATCH <<<"${CURRENT}"
NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))"
echo "Bumping setup.py ${CURRENT} -> ${NEW_VERSION}"

python - <<PY
from pathlib import Path
path = Path("setup.py")
text = path.read_text(encoding="utf-8")
old = 'version="${CURRENT}"'
new = 'version="${NEW_VERSION}"'
if old not in text:
    raise SystemExit(f"expected {old!r} in setup.py")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
PY

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add setup.py
git commit -m "chore: bump version to ${NEW_VERSION} [skip ci]"
git push origin HEAD:main

TAG="v${NEW_VERSION}"
git tag -a "${TAG}" -m "Release ${TAG}"
git push origin "${TAG}"

gh release create "${TAG}" \
  --title "${TAG}" \
  --notes "Weekly release ${TAG} (auto). Commits since ${LATEST_TAG:-beginning}: ${COMMIT_COUNT}."

if [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "outcome=released" >> "$GITHUB_OUTPUT"
  echo "version=${NEW_VERSION}" >> "$GITHUB_OUTPUT"
fi
echo "Released ${TAG}"
