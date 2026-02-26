---
name: download-files
description: Download all files from a selected Israeli supermarket scraper and optionally validate the download. Use when the user wants to download scraper data for one or more scrapers, run a full scrape for a chosen chain, or validate download quality.
---

# Download All Files (Selected Scraper)

Download every file produced by one or more selected scrapers to disk, then optionally run validation to report counts and sizes.

## When to use

- User asks to "download all files" for a scraper or "run scraper X".
- User wants to pull full data for a specific chain (e.g. Victory, Shufersal).
- User wants to validate download quality after a run.

## 1. Select scraper(s)

Valid names are the `ScraperFactory` enum names (e.g. `VICTORY`, `SHUFERSAL`, `BAREKET`, `RAMI_LEVY`). List all with:

```bash
python -c "from il_supermarket_scarper import ScraperFactory; print(ScraperFactory.all_scrapers_name())"
```

Use a single name or comma-separated list for multiple scrapers.

## 2. Download all files to disk

Run the project's main entrypoint with disk output and the selected scraper(s). No limit, single pass so all files are downloaded once.

```bash
ENABLED_SCRAPERS=<scraper_name> OUTPUT_MODE=disk SINGLE_PASS=true python main.py
```

Examples:

```bash
# One scraper
ENABLED_SCRAPERS=VICTORY SINGLE_PASS=true python main.py

# Multiple scrapers (comma-separated, no spaces)
ENABLED_SCRAPERS=VICTORY,SHUFERSAL SINGLE_PASS=true python main.py
```

Optional env:

- `STORAGE_PATH` — where to save files (default: `dumps`). Files go under `STORAGE_PATH/<scraper_name>/`.
- `STATUS_DATABASE_PATH` — status DB path (default: `dumps/status`).

Do **not** set `LIMIT` when downloading "all" files.

## 3. Validate download (optional)

To get a report of file counts, sizes, and sample links (no extra download), run the validation script with the same scraper selection:

```bash
ENABLED_SCRAPERS=<scraper_name> python .cursor/skills/download-files/validate_download_quality.py
```

Reports are written under `.cursor/skills/download-files/`:

- `validation_report.json` — full per-scraper file list and metadata.
- `validation_summary.txt` — short human-readable summary.

To validate all scrapers:

```bash
ENABLED_SCRAPERS=all python .cursor/skills/download-files/validate_download_quality.py
```

## Summary

| Goal | Command |
|------|--------|
| Download all files (one/more scrapers) | `ENABLED_SCRAPERS=NAME SINGLE_PASS=true python main.py` |
| Validate (report only) | `ENABLED_SCRAPERS=NAME python .cursor/skills/download-files/validate_download_quality.py` |

The validation script uses the same scraping pipeline as the project (see `validate_download_quality.py`) but with an in-memory queue; it does not write files. Use `main.py` with `OUTPUT_MODE=disk` to actually save files.
