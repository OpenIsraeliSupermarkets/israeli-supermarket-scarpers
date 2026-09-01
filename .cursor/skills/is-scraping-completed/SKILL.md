---
name: is-scraping-completed
description: Validate that Israeli supermarket scrapers retrieve every file available on the chain's UI/site (UI ⊆ scraper). Use when checking scraper availability, comparing site vs API listings, inspecting gov.il CPFTA portals, or troubleshooting missing files.
---

# Inspect / Validate Supermarket Sites

## Core principle (do not forget)

**UI inventory ≠ scraper logic.**

To know what the **site/UI** exposes, navigate the **real UI** (or the human-facing listing view) and read filenames from that view:

1. Open the chain portal URL.
2. Follow the **click / filter path** (XPaths below) until the page that lists downloadable files.
3. Collect filenames from that listing (all pages / filters a user can reach).

The **scraper** side is separate and only uses:

`scraper.collect_files_details_from_site(...)`  
(instantiated via `ScraperFactory.<NAME>.value` — do **not** filter to “stable” unless asked)

Expectation:

`ui_filenames_from_browser_listing ⊆ scraper_collect_files_details_from_site`

### Anti-patterns

| Do | Do not |
|---|---|
| Click through UI XPaths / filters to the file table | Reimplement `site_names_*` that mirror the engine’s API/HTML crawl |
| Read names from the visible listing (or SPA grid after user filters) | Call the same JSON/FTP helpers the scraper uses and call that “UI” |
| Use browser when the site is HTML/SPA | Assume `generate_all_files()` is an independent UI check |

`scripts/validate_ui_vs_scraper.py` is a **smoke/approx** helper (especially for FTP / JSON-only backends). It is **not** a substitute for documenting and following the UI click path. Prefer browser + this skill’s XPaths for HTML portals.

Do **not** call `scrape()` for discovery — it downloads.

Listing PASS does not prove files fetch. After this skill, use
[`is-download-completed`](../is-download-completed/SKILL.md)
(`scripts/validate_downloads.py`): it calls `scrape()` with a fresh status DB
and **stops on the first download or extract failure**.

---

## Agent workflow

1. Resolve the chain’s portal URL (table below or `scripts/dump_gov_il_links.py`).
2. Open that URL in the browser (use browser tools when the listing is HTML/SPA).
3. Follow **UI navigation → file list** for that engine (XPaths / filters in the next section).
4. Record `ui_count` / sample names from the listing UI (all pages a user can open).
5. Separately run list-only scraper discovery: `collect_files_details_from_site`.
6. Compare: `ui_not_in_scraper` must be `0`.
7. On **FAIL**: stay on that chain’s portal; check filters, date, pagination, chain id in filenames.
8. On gov.il **403**: skip live registry; use URL tables / `dump_gov_il_links.py --fallback-only`.

Optional smoke (not the independent UI path):

```bash
python scripts/validate_ui_vs_scraper.py --per-engine
python scripts/validate_ui_vs_scraper.py --scrapers QUIK,BAREKET,TIV_TAAM
python scripts/validate_ui_vs_scraper.py --all-listed --output scripts/validation_ui_vs_scraper.json

python scripts/dump_gov_il_links.py --output scripts/gov_il_links.json
python scripts/dump_gov_il_links.py --fallback-only
```

### Yield-order footgun (scraper side only)

- Web / ApiWeb / MultiPageWeb: `collect_files_details_from_site` yields `(url, name)`.
- Cerberus: yields `(name, url)`.

---

## UI navigation → where files are listed

Use these as the **click path to the listing**, then read the table/grid. XPaths are taken from scraper DOM usage so agents know **where to look/click**, not so they re-run the engine.

### MultiPageWeb — Shufersal-style (`gridContainer`)

| Step | Action |
|---|---|
| Land | Open scraper `url` (e.g. `https://prices.shufersal.co.il/`) |
| Filters | Category / store UI → maps to `FileObject/UpdateCategory?catID=` (1–5) and optional `storeId` |
| File rows | `//*[@id="gridContainer"]/table/tbody/tr` |
| Download link | `./td[1]/a` |
| Last page hint | `//*[@id="gridContainer"]/table/tfoot/tr/td/a[6]/@href` |
| Paginate | Walk `page=1..N` (no dedicated “Next” XPath in repo) |

### MultiPageWeb — Hazi Hinam

| Step | Action |
|---|---|
| Land | `https://shop.hazi-hinam.co.il/Prices` |
| Filters | Date `d`, type `t` (1=price, 2=promo, 3=store), flag `f` |
| File rows | `//table/tbody/tr` |
| Filename cell | `td[3]` |
| Download link | `td[6]/a` |
| Last page | `(//li[contains(concat(' ', normalize-space(@class), ' '), ' pagination-item ')])[last()]/a` |
| Paginate | `p=` query |

### MultiPageWeb — City Market Shops

| Step | Action |
|---|---|
| Land | `http://www.citymarket-shops.co.il/` |
| Filters | Date `d`, store `s`, type/full `t` / `f` |
| File rows | `//table/tbody/tr` |
| Filename cell | `td[3]` |
| Download link | `td[7]/a` |
| Last page | Same `li.pagination-item` last-link XPath as Hazi Hinam |

### MultiPageWeb — Super Pharm

| Step | Action |
|---|---|
| Land | `http://prices.super-pharm.co.il/` |
| Filters | Category (`Category-equals=Stores\|Price\|PriceFull\|PromoFull`), optional date |
| File rows | `//tbody/tr` |
| Filename cell | `./td[2]` |
| Download link | `./td[6]/a` |
| Last page | `//*[@class="mvc-grid-pager"]/button[last()]/@data-page` |

### WebBase — single HTML table

| Step | Action |
|---|---|
| Land | Open scraper `url` |
| Listing | First data table; rows after header; first `<a>` per row is the file |
| Paginate | Usually none |

Special cases:

- **Wolt**: day pages `.../v1/{YYYY-MM-DD}.html` — list items are `<li>` + link (not a price grid).
- **MESHMAT_YOSEF_1**: JSON body at the worker URL — **no clickable table**.

### Bina (human UI: `Main.aspx`; scraper JSON: `MainIO_Hok.aspx`)

| Step | Action |
|---|---|
| Land | `http://{host}.binaprojects.com/Main.aspx` (example BAREKET: `https://superbareket.binaprojects.com/Main.aspx`) |
| Filters | `#wReshet` (רשת), `#wStore` (מחסן), `#wFileType` (סוג; default הכל=0), `#wDate` (מתאריך) |
| List files | Click `//*[@id="Button1"]` (green ✓ → `onload1()` → fills `#myTable`) |
| Filename cells | `//*[@id="myTable"]//tr[td]/td[1]` |
| Download | Per-row button / `Download.aspx?FileNm=...` |

Encoded for BAREKET in `scripts/validate_ui_vs_scraper.py` → `UIEngine.BAREKET`. Do **not** treat a direct `MainIO_Hok.aspx` JSON fetch as the UI path.

### PublishPrice (Quik / Carrefour / Mega)

| Step | Action |
|---|---|
| Land | `https://prices.{site}.co.il/` (optional `?p=./YYYYMMDD` for a date folder) |
| Listing | Paginated UI is driven by embedded `const files = [...]` in a `<script>` — walk the **on-page file list / pager**, not a parallel parse of that script labeled as independent UI |
| Table XPath | None in repo |

### ApiWeb / laibcatalog SPA

| Step | Action |
|---|---|
| Land | SPA e.g. `https://laibcatalog.co.il/victory/index.html` (also `mshuk`, `hcohen`) |
| Filters | Pick branch / filters in the SPA until the files grid is populated |
| Listing | Visible grid filenames (SPA loads `getbranches` + `getfiles` under the hood — **do not** call those APIs yourself and call it UI) |
| Table XPath | None in repo (JSON-backed SPA) |

### Matrix (legacy ASPX table)

| Step | Action |
|---|---|
| Land | `https://laibcatalog.co.il/NBCompetitionRegulations.aspx` (or scraper `url`) |
| Listing | HTML `<tr>` rows; keep rows containing the chain’s Hebrew name; file = row link |
| Prefer | Factory often uses `*_NEW_SOURCE` (ApiWeb SPA) instead |

### Cerberus (FTP) — no browser UI

| Step | Action |
|---|---|
| Access | FTP `url.retail.publishedprices.co.il` with chain user (password usually empty) |
| Listing | Directory listing at `/` or path like `/Yuda` — **no XPath** |
| Note | “UI” here is the FTP directory a user would browse with an FTP client |

---

## Gov.il registry

**URL:** https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations  
(alt: https://www.gov.il/he/pages/cpfta_prices_regulations)

May block non-IL IPs (Cloudflare 403). `dump_gov_il_links.py` falls back to the skill URL table automatically. Browser CDP can still scrape a live gov.il session when available.

Local Cache in: il_supermarket_scarper/utils/tests/cpfta_prices_regulations
---

## Checklist

- [ ] Portal reachable
- [ ] Reached the **file listing view via UI path** (XPaths / filters above) — not via scraper-equivalent code
- [ ] `ui_count` from that listing; `scraper_count` from `collect_files_details_from_site`
- [ ] `ui_not_in_scraper == 0` (PASS)
- [ ] Files recent (1–3 days) when investigating FAIL
- [ ] Chain id in filenames matches scraper `chain_id`
- [ ] Unstable / DNS-dead chains recorded (e.g. QUIK) — do not silently skip

## Common issues

| Symptom | Likely cause |
|---|---|
| `ui_not_in_scraper > 0` | Scraper filter/XPath/EDI bug vs what the UI lists |
| Site unreachable / DNS | Chain down; may be why scraper is stability-disabled |
| ApiWeb empty secondary EDI | SPA/primary EDI may still show files — check UI branch picker |
| Paginated UI “page 1 only” | Must open **all** UI pages / last-page control |
| Validated with scraper twin logic | Invalid check — redo via browser/UI path |
| gov.il 403 | Non-IL IP — use skill URLs or `dump_gov_il_links.py` fallback |
| Cerberus name mismatch in ad-hoc code | Yield order is `(name, url)`, not `(url, name)` |
