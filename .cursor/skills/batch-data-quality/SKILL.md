---
name: batch-data-quality
description: Run data-quality validation for all (or a subset of) Israeli supermarket scrapers from ScraperFactory. Use when the user wants to validate data quality for every scraper, run data quality in batch, or "data quality for all scrapers".
---

# Batch Data Quality

Run the **data-quality** workflow (see [@.cursor/commands/data-quliaty.md](../../commands/data-quliaty.md)) for each scraper. One full pass per scraper; only after each run completes do you compare and report, then move to the next.

## Scope

- **All scrapers**: Use the list from `ScraperFactory` (same as in `il_supermarket_scarper/scrappers_factory.py`). Get names with:
  ```bash
  python -c "from il_supermarket_scarper import ScraperFactory; print(ScraperFactory.all_scrapers_name())"
  ```
- **Subset**: If the user names specific scrapers, run only those. Otherwise run for every name returned by `all_scrapers_name()`.

## Workflow (per scraper)

For **each** scraper name in scope:

1. **Download** – Use **@.cursor/skills/download-files**: `ENABLED_SCRAPERS=<name> OUTPUT_MODE=disk SINGLE_PASS=true python main.py`. **Wait for completion** (no timeout, no background).
2. **Optional validation script** – If you run it: `ENABLED_SCRAPERS=<name> python .cursor/skills/download-files/validate_download_quality.py`. Wait for it to finish.
3. **Web** – Use **@.cursor/skills/scroll-like-a-human**: open the official price-transparency page (or `il_supermarket_scarper/utils/tests/cpfta_prices_regulations`), go to that retailer, enter password if needed, scroll/snapshot and record every file/link the site shows.
4. **Compare** – Align scraped files (disk or `validation_report.json`) with the browser list. Report for this scraper: same count/names, missing, extra, mismatches.
5. Then proceed to the **next** scraper.

## Full-pass rule

Do **not** start the next scraper until the current one’s download (and validation, if run) has **finished** and the compare step is done. No short timeouts or partial-result reporting.

## Final summary

After all scrapers in scope are done, provide a short summary table or list: scraper name, pass/fail or status, and any critical mismatches (e.g. missing files).
