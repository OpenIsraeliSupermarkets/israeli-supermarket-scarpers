# Data quality validation agent

Given a **scraper name**, validate quality by downloading today’s data, fetching what the official site shows, and comparing both.

## Full pass (required)

**Always do a full pass:** wait for the download (and validation, if run) to **complete** before comparing. Do not use a short timeout or background the download; do not report on partial results. Only after the run has finished, compare scraped files with the official list and then report.

## Workflow

1. **Download today’s files** – Use **@.cursor/skills/download-files**: with the given scraper name, download all files for today (no limit, single pass).
2. **Get what the web shows** – Use **@.cursor/skills/scroll-like-a-human**: open the official price-transparency page (or the HTML file with retailer links/passwords), navigate to the retailer’s site for that scraper, enter the password if required, and collect the files/links the site displays (e.g. by scrolling and snapping the page).
3. **Compare both** – Compare the downloaded/scraped file list (and optionally sample content) with the list you collected from the browser. Report matches, missing files, or extra files.

## 1. Download (download-files skill)

- List scrapers: `python -c "from il_supermarket_scarper import ScraperFactory; print(ScraperFactory.all_scrapers_name())"`
- Download for today: `ENABLED_SCRAPERS=<scraper_name> OUTPUT_MODE=disk SINGLE_PASS=true python main.py` — **run to completion** (no short timeout; wait for the process to finish).
- Optional report: `ENABLED_SCRAPERS=<scraper_name> python .cursor/skills/download-files/validate_download_quality.py` → `validation_report.json`, `validation_summary.txt` — if run, **wait for it to finish** before comparing.

## 2. Web (scroll-like-a-human skill)

- Source: Israeli Consumer Protection (הרשות להגנת הצרכן ולסחר הוגן) price-transparency page; local HTML path: `il_supermarket_scarper/utils/tests/cpfta_prices_regulations` (or the official page it links to).
- Use browser MCP: open the retailer URL for the scraper, enter password if needed, scroll/snapshot the page, and record every file/link the site shows.

## 3. Compare

- Align scraped files (from disk or `validation_report.json`) with the list from the browser.
- Summarize: same count and names, missing on our side, extra on our side, or mismatches.
