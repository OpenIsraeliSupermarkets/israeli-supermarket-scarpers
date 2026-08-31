# Secrets for weekly hybrid release

Primary auth is a **GitHub App** (installation token minted each job). It does not expire.
Configure once at the **org** (Settings → Secrets and variables → Actions). Grant repository access to these three repos (or all private).

## GitHub App (required)

| Name | Where | Purpose |
|------|--------|---------|
| `APP_CLIENT_ID` | Org **variable** | GitHub App client ID |
| `APP_PRIVATE_KEY` | Org **secret** | App private key (PEM). Rotate only if leaked. |

### Create and install (one-time)

1. Org → Settings → Developer settings → GitHub Apps → **New GitHub App**.
2. Suggested name: `ois-release`. Homepage: `https://github.com/OpenIsraeliSupermarkets`.
3. Uncheck **Webhook → Active** (this App is for API tokens only).
4. Repository permissions:
   - **Actions:** Read (coordinator `gh run list`)
   - **Contents:** Read and write (checkout, push, tags, releases, `repository_dispatch`)
   - **Issues:** Read and write (parsers sync + daily-publish deps issues)
   - **Pull requests:** Read and write (coordinator bump PR)
   - **Metadata:** Read (default)
5. Install on this account only, then **Install** on:
   - `israeli-supermarket-scarpers`
   - `israeli-supermarket-parsers`
   - `daily-publish-supermarket-data`
6. Generate a **private key**, paste the PEM into org secret `APP_PRIVATE_KEY`.
7. Copy the App **Client ID** into org variable `APP_CLIENT_ID`.
8. On **scrapers** and **parsers** `main` branch protection: **Allow specified actors to bypass required pull requests** → add `ois-release` (or whatever you named the App). `github.token` cannot push to protected `main`; the App can if it is a bypass actor.

Workflows mint a 1-hour installation token with `actions/create-github-app-token` when `APP_CLIENT_ID` is set, scoped to those three repos.

## Cursor Automations (still secrets)

| Secret | Repo(s) | Purpose |
|--------|---------|---------|
| `CURSOR_MAINTAINER_WEBHOOK` | scrapers, parsers, daily-publish | POST after a new CI / sync / deps issue |
| `CURSOR_WEBHOOK_SECRET` | same | optional Bearer |
| `PARSERS_MAINTAINER_WEBHOOK` | scrapers | parsers maintainer URL (same as parsers `CURSOR_MAINTAINER_WEBHOOK`) |
| `PARSERS_MAINTAINER_WEBHOOK_SECRET` | scrapers | optional Bearer |

## Deprecated PAT fallbacks

Used only when `APP_CLIENT_ID` is unset. Delete after the App path is green.

| Secret | Repo(s) | Purpose |
|--------|---------|---------|
| `RELEASE_GITHUB_TOKEN` | scrapers, parsers | PAT to push version bump + tags |
| `PARSERS_REPO_TOKEN` | scrapers | PAT with `issues:write` on parsers |
| `DAILY_PUBLISH_DISPATCH_TOKEN` | scrapers, parsers | PAT: `contents:write` (repo dispatch) + `issues:write` on daily-publish |
| `WEEKLY_COORDINATOR_TOKEN` | daily-publish | PAT: read Actions on scrapers+parsers; push branch + open PR |

## Cursor Automations (manual)

1. Scrapers: webhook trigger → maintainer (CI issues).
2. Parsers: webhook trigger → maintainer (CI + `[sync]` issues; may noop).
3. Daily-publish: webhook trigger → maintainer (`[deps]` issues from scrapers/parsers releases).
