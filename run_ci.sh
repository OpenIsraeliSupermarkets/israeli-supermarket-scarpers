#!/bin/bash
# Simulates all locally-runnable CI checks from .github/workflows/.
#
# Mirrors:
#   test-suite.yml  → Step: Tests
#   pylint.yml      → Step: Lint
#   docs.yml        → Step: Docs
#
# Skipped (require GitHub Actions infra):
#   codeql.yml, user-validation.yml, docker-publish.yml, python-publish.yml
#
# Usage: ./run_ci.sh [--no-cache] [--skip-tests] [--skip-lint] [--skip-docs] [N]
#   N             number of pytest-xdist workers (default: 8)
#   --no-cache    pass --no-cache to docker build
#   --skip-tests  skip the test stage
#   --skip-lint   skip the lint stage
#   --skip-docs   skip the docs stage

set -euo pipefail

N=8
NO_CACHE=""
RUN_TESTS=true
RUN_LINT=true
RUN_DOCS=true

for arg in "$@"; do
    case "$arg" in
        --no-cache)   NO_CACHE="--no-cache" ;;
        --skip-tests) RUN_TESTS=false ;;
        --skip-lint)  RUN_LINT=false ;;
        --skip-docs)  RUN_DOCS=false ;;
        [0-9]*)       N="$arg" ;;
    esac
done

PASS=0
FAIL=0
FAILURES=()

print_step() { echo; echo "==> $1"; }
pass()       { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail()       { echo "FAIL: $1"; FAIL=$((FAIL + 1)); FAILURES+=("$1"); }

# ---------------------------------------------------------------------------
# Step 1: Tests  (mirrors test-suite.yml)
# ---------------------------------------------------------------------------
if $RUN_TESTS; then
    print_step "Tests (test-suite.yml) — N=${N} workers"

    # Free disk space: remove dangling/unused Docker images
    echo "Pruning unused Docker images..."
    docker image prune -f 2>/dev/null || true

    if docker build $NO_CACHE -t erlichsefi/israeli-supermarket-scarpers:test --target test .; then
        (docker stop scraper-test-run 2>/dev/null || true) && (docker rm scraper-test-run 2>/dev/null || true)
        if docker run --rm --name scraper-test-run \
               -e "PYTEST_WORKERS=${N}" \
               erlichsefi/israeli-supermarket-scarpers:test; then
            docker builder prune -f 2>/dev/null || true
            pass "Tests"
        else
            fail "Tests"
        fi
    else
        fail "Tests (build)"
    fi
fi

# ---------------------------------------------------------------------------
# Step 2: Lint  (mirrors pylint.yml)
# ---------------------------------------------------------------------------
if $RUN_LINT; then
    print_step "Lint (pylint.yml)"

    if docker build $NO_CACHE --target lint -t lint-image .; then
        if docker run --rm lint-image; then
            pass "Lint"
        else
            fail "Lint"
        fi
    else
        fail "Lint (build)"
    fi
fi

# ---------------------------------------------------------------------------
# Step 3: Docs  (mirrors docs.yml)
# ---------------------------------------------------------------------------
if $RUN_DOCS; then
    print_step "Docs (docs.yml)"

    if python -m pip install --quiet -r requirements-dev.txt && \
       python -m pip install --quiet -e . && \
       (cd docs && sphinx-apidoc -o source/api ../il_supermarket_scarper --separate --force) && \
       (cd docs && make html SPHINXOPTS="-W"); then
        pass "Docs"
    else
        fail "Docs"
    fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print_step "Summary"
echo "Passed: ${PASS}  Failed: ${FAIL}"
if [ ${#FAILURES[@]} -gt 0 ]; then
    echo "Failed steps: ${FAILURES[*]}"
    exit 1
fi
echo "All CI steps passed."
