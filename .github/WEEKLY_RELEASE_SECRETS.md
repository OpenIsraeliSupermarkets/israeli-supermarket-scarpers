# Secrets for weekly hybrid release (configure in GitHub repo Settings → Secrets)

## israeli-supermarket-scarpers
| Secret | Required | Purpose |
|--------|----------|---------|
| `CURSOR_MAINTAINER_WEBHOOK` | for maintainer | POST after new CI issue |
| `CURSOR_WEBHOOK_SECRET` | optional | Bearer token for webhook |
| `PARSERS_REPO_TOKEN` | for sync issue | PAT with `issues:write` on parsers |
| `PARSERS_MAINTAINER_WEBHOOK` | for sync | parsers maintainer webhook URL (same as parsers `CURSOR_MAINTAINER_WEBHOOK`) |
| `PARSERS_MAINTAINER_WEBHOOK_SECRET` | optional | Bearer for that webhook |
| `RELEASE_GITHUB_TOKEN` | if main protected | PAT to push version bump + tags |
| `DAILY_PUBLISH_DISPATCH_TOKEN` | for coordinator signal | PAT with `actions:write` (repo dispatch) on daily-publish |

## israeli-supermarket-parsers
| Secret | Required | Purpose |
|--------|----------|---------|
| `CURSOR_MAINTAINER_WEBHOOK` | for maintainer | POST after new CI / sync issue |
| `CURSOR_WEBHOOK_SECRET` | optional | Bearer token |
| `RELEASE_GITHUB_TOKEN` | if main protected | PAT to push version bump + tags |
| `DAILY_PUBLISH_DISPATCH_TOKEN` | for coordinator signal | same as scrapers |

## daily-publish-supermarket-data
| Secret | Required | Purpose |
|--------|----------|---------|
| `WEEKLY_COORDINATOR_TOKEN` | yes | PAT: read Actions on scrapers+parsers; push branch + open PR here |

## Cursor Automations (manual)
1. Scrapers: webhook trigger → maintainer (CI issues).
2. Parsers: webhook trigger → maintainer (CI + `[sync]` issues; may noop).
