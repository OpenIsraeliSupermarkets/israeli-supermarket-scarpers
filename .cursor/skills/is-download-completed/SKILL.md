---
name: is-download-completed
description: Download every file an Israeli supermarket scraper lists and stop on the first download or extract failure. Second-tier check after is-scraping-completed (listing). Use when verifying listed files actually download, diagnosing wget/SAS/extract failures, or after a listing-only PASS.
disable-model-invocation: true
---

# Download / Validate Supermarket Files

## Core principle

**Listing completeness ≠ download completeness.**

`is-scraping-completed` only checks `UI ⊆ collect_files_details_from_site`. It must **not** call `scrape()`.

This skill **does** call `scrape()`. Expectation:

every file the scraper would collect **downloads and extracts**

Stop at the **first** download or extract failure. Do not keep scraping the rest of the chain.

**Exception — `source_corrupt`:** if the remote published a truncated/bad archive (full-size download, extract still fails after retries), the scraper marks `source_corrupt=True`. Validation **skips** those files (`skipped_corrupt`) and continues. That is not a fetch bug.

## When to use

| Use this skill | Use `is-scraping-completed` instead |
|---|---|
| wget / SAS / User-Agent download errors | UI lists files the scraper does not see |
| `extract_succefully=False` | Pagination / XPath / EDI listing gaps |
| After listing PASS, prove files fetch | Discovery-only / no download |

Run listing first when both matter. A listing PASS with a download FAIL is still a real bug.

## Do not confuse with daily-publish skip

Daily-publish **skips** files already in `verified_downloads` (even after dumps are cleaned). That skip is **by design** — not a download failure.

This check uses a **fresh dump dir** and a status DB that never reports `already_downloaded`, so every listed file is actually fetched. Do **not** reuse a production status JSON.

## Agent workflow

1. Resolve `ScraperFactory` names (user list, or one sample per engine).
2. Run the helper (it instantiates via `ScraperFactory.<NAME>.value`, **not** stable-only):

```bash
python scripts/validate_downloads.py --scrapers SHUFERSAL
python scripts/validate_downloads.py --scrapers SHUFERSAL,VICTORY_NEW_SOURCE
python scripts/validate_downloads.py --per-engine
python scripts/validate_downloads.py --all-listed --output scripts/validation_downloads.json
```

3. Default is **all files**, fail-fast. Use `--limit N` only when the user asks for a cheaper smoke.
4. On **FAIL**: record `failed_file`, `error`, how many succeeded before the stop. Stay on that chain; do not move on until the failure is understood.
5. On **PASS**: `failed=0` and `downloaded > 0` (optional `skipped_corrupt > 0` is OK).

`scrape()` may have a few in-flight downloads (`max_threads`). Breaking the generator cancels the rest; report the first failed result.

## Checklist

- [ ] Fresh status (no `verified_downloads` skip)
- [ ] `scrape()` used (not list-only discovery)
- [ ] Stopped on first download/extract failure (source_corrupt skips continue)
- [ ] `downloaded > 0` and `failed == 0` (PASS)
- [ ] First failure includes filename + error (FAIL)

## Common issues

| Symptom | Likely cause |
|---|---|
| `wget: not found` / SAS `&amp;` in URL | Download path (`requests` / wget fallback) |
| First file fails, rest not tried | Expected — fail-fast |
| `skipped_corrupt` / `source corrupt after N downloads` | Remote truncated gzip; not a scraper bug |
| `no files downloaded` | Empty listing or filters; confirm with listing skill |
| PASS here, quality `saw>0 downloaded=0` | Prior `verified_downloads` skip — not a fetch bug |
