#!/usr/bin/env bash
# Change-gate weekly release: noop if no commits since last v* tag; else tag and release.
# Bumps setup.py patch only when it still matches the latest v* tag (skip if already bumped).
# Re-runnable: an existing tag or release is reused instead of failing.
# Env: GH_TOKEN / GITHUB_TOKEN (contents write; App installation token or PAT), GITHUB_REPOSITORY
# Outputs via GITHUB_OUTPUT when present: outcome=noop|released, version=...
set -euo pipefail

if [ "${GITHUB_REF_NAME:-}" != "main" ]; then
  echo "Refusing to run weekly release outside main (got: ${GITHUB_REF_NAME:-unset}). This script pushes directly to main; only run it from main." >&2
  exit 1
fi

# Must precede any commit or annotated tag, both of which need an author.
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

emit_output() {
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "outcome=$1" >> "$GITHUB_OUTPUT"
    if [ -n "${2:-}" ]; then
      echo "version=$2" >> "$GITHUB_OUTPUT"
    fi
  fi
}

create_release() {
  local tag="$1"
  local start_tag="${2:-}"
  local args=(--title "${tag}" --generate-notes)
  if [ -n "${start_tag}" ]; then
    args+=(--notes-start-tag "${start_tag}")
  fi
  gh release create "${tag}" "${args[@]}"
}

git fetch --tags --force origin
LATEST_TAG=$(git tag -l 'v*' --sort=-v:refname | head -n 1 || true)
export LATEST_TAG
if [ -z "${LATEST_TAG}" ]; then
  echo "No existing v* tags; treating all history as candidates."
  COMMIT_COUNT=$(git rev-list --count HEAD)
else
  COMMIT_COUNT=$(git rev-list --count "${LATEST_TAG}..HEAD")
fi
echo "Latest tag: ${LATEST_TAG:-<none>}; commits since: ${COMMIT_COUNT}"

if [ "${COMMIT_COUNT}" -eq 0 ]; then
  # A previous run can die after pushing the tag but before creating the release,
  # which leaves nothing to publish from. Finish that release instead of nooping.
  if [ -n "${LATEST_TAG}" ] && ! gh release view "${LATEST_TAG}" >/dev/null 2>&1; then
    PREVIOUS_TAG=$(git tag -l 'v*' --sort=-v:refname | sed -n 2p || true)
    echo "Tag ${LATEST_TAG} has no GitHub release; creating it."
    create_release "${LATEST_TAG}" "${PREVIOUS_TAG}"
    emit_output released "${LATEST_TAG#v}"
    exit 0
  fi
  emit_output noop
  echo "No commits since last tag; noop."
  exit 0
fi

if ! VERSION_INFO=$(python - <<'PY'
import os
import re
import sys
from pathlib import Path


def parse_version(value):
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        sys.exit(f"unsupported version {value!r} in setup.py (expected MAJOR.MINOR.PATCH)")
    return tuple(int(part) for part in parts)


text = Path("setup.py").read_text(encoding="utf-8")
match = re.search(r'version\s*=\s*"([^"]+)"', text)
if not match:
    sys.exit("version= not found in setup.py")
current = match.group(1)
current_parts = parse_version(current)

tag = os.environ.get("LATEST_TAG", "")
tag_version = tag[1:] if tag.startswith("v") else tag

if tag_version and current_parts > parse_version(tag_version):
    print(f"yes {current} {current}")
else:
    major, minor, patch = current_parts
    print(f"no {current} {major}.{minor}.{patch + 1}")
PY
); then
  echo "Failed to determine the release version from setup.py." >&2
  exit 1
fi

read -r SKIP_BUMP CURRENT_VERSION NEW_VERSION <<<"${VERSION_INFO}"
if [ "${SKIP_BUMP}" != "yes" ] && [ "${SKIP_BUMP}" != "no" ]; then
  echo "Unexpected version computation output: ${VERSION_INFO}" >&2
  exit 1
fi
if ! [[ "${NEW_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Refusing to release invalid version: '${NEW_VERSION}'" >&2
  exit 1
fi

if [ "${SKIP_BUMP}" = "yes" ]; then
  echo "setup.py already at ${NEW_VERSION} (latest tag ${LATEST_TAG:-<none>}); skipping bump."
else
  echo "Bumping setup.py ${CURRENT_VERSION} -> ${NEW_VERSION}"

  CURRENT_VERSION="${CURRENT_VERSION}" NEW_VERSION="${NEW_VERSION}" python - <<'PY'
import os
from pathlib import Path

path = Path("setup.py")
text = path.read_text(encoding="utf-8")
old = 'version="{}"'.format(os.environ["CURRENT_VERSION"])
new = 'version="{}"'.format(os.environ["NEW_VERSION"])
if old not in text:
    raise SystemExit(f"expected {old!r} in setup.py")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
PY

  git add setup.py
  git commit -m "chore: bump version to ${NEW_VERSION} [skip ci]"
  git push origin HEAD:main
fi

TAG="v${NEW_VERSION}"

if git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; then
  echo "Tag ${TAG} already exists locally; reusing it."
else
  git tag -a "${TAG}" -m "Release ${TAG}"
fi

if git ls-remote --exit-code --tags origin "refs/tags/${TAG}" >/dev/null 2>&1; then
  echo "Tag ${TAG} already on origin; not pushing."
else
  git push origin "${TAG}"
fi

if gh release view "${TAG}" >/dev/null 2>&1; then
  echo "Release ${TAG} already exists; leaving it as is."
else
  create_release "${TAG}" "${LATEST_TAG}"
fi

emit_output released "${NEW_VERSION}"
echo "Released ${TAG}"
