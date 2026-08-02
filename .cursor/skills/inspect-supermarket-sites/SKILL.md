---
name: inspect-supermarket-sites
description: Validate that Israeli supermarket scrapers retrieve every file available on the chain's UI/site (UI ⊆ scraper). Use when checking scraper availability, comparing site vs API listings, inspecting gov.il CPFTA portals, or troubleshooting missing files.
---

# Inspect / Validate Supermarket Sites

## Expectation

When the scraper runs in Python (list-only discovery), **all files downloadable via the UI/site must be retrieved**:

`site_file_set ⊆ scraper_collect_files_details_from_site`

Do **not** filter to “stable” scrapers unless the user asks — instantiate via `ScraperFactory.<NAME>.value`.

Prefer scripts over browser screenshots. Use the browser only when HTTP/FTP listing fails.

---

## Effortless commands

From the repo root (package installed / `PYTHONPATH` set):

```bash
# One sample per engine (default smoke)
python scripts/validate_ui_vs_scraper.py --per-engine

# Specific chains (including unstable)
python scripts/validate_ui_vs_scraper.py --scrapers QUIK,BAREKET,TIV_TAAM

# Every ScraperFactory member (slow; includes stability-disabled)
python scripts/validate_ui_vs_scraper.py --all-listed --output scripts/validation_ui_vs_scraper.json

# Dump portal URL map once (live gov.il, or skill fallback on Cloudflare 403)
python scripts/dump_gov_il_links.py --output scripts/gov_il_links.json
python scripts/dump_gov_il_links.py --fallback-only   # skip network to gov.il
```

`validate_ui_vs_scraper.py` exits `1` if any chain has UI files missing from the scraper set.

Report fields: `ui_count`, `scraper_count`, `ui_not_in_scraper`, `missing_sample`, `enabled_by_factory`, `engine`.

---

## Agent workflow

1. Run `scripts/validate_ui_vs_scraper.py` for the requested scope (`--per-engine` unless told otherwise).
2. Optionally run `scripts/dump_gov_il_links.py` to confirm gov.il portal URLs match scraper URLs.
3. On **FAIL**: open only that chain’s portal (skill URL table or gov.il JSON) and diagnose.
4. On gov.il **403**: skip registry; use fallback URLs below.
5. Do **not** call `scrape()` for discovery counts — it downloads. Validation uses `collect_files_details_from_site`.

### Yield-order footgun

- Web / ApiWeb / MultiPageWeb: `collect_files_details_from_site` yields `(url, name)`.
- Cerberus: yields `(name, url)`.
- The validate script handles both via `pick_filename`.

---

## How site inventory is collected (by engine)

| Engine | Site / UI source | Notes |
|---|---|---|
| PublishPrice | HTTP page `const files = [...]` | Same array the paginated UI renders |
| Bina | `MainIO_Hok.aspx` JSON (`FileNm`) | Query `_=<chain_id>&WFileType=0` |
| ApiWeb | `/webapi/api/getbranches` + `getfiles` | Same backend as laibcatalog SPA |
| MultiPageWeb / WebBase | `generate_all_files()` HTML crawl | Full pagination, not page-1 only |
| Cerberus | FTP `MLSD`/`NLST` | No browser; host `url.retail.publishedprices.co.il` |
| Matrix | ASPX table filtered by Hebrew name | Legacy; factory often uses `*_NEW_SOURCE` instead |

---

## Gov.il registry

**URL:** https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations  
(alt: https://www.gov.il/he/pages/cpfta_prices_regulations)

May block non-IL IPs (Cloudflare 403). `dump_gov_il_links.py` falls back to the skill URL table automatically. Browser CDP can still scrape a live gov.il session when available.

---

## Scraper → URL reference

### Web UI

| ScraperFactory | Hebrew | Engine | URL |
|---|---|---|---|
| BAREKET | עוף והודו ברקת | Bina | http://superbareket.binaprojects.com/MainIO_Hok.aspx |
| CITY_MARKET_KIRYATGAT | סיטי מרקט | Bina | http://citymarketkiryatgat.binaprojects.com/MainIO_Hok.aspx |
| CITY_MARKET_SHOPS | סיטי מרקט | MultiPageWeb | http://www.citymarket-shops.co.il/ |
| GOOD_PHARM | גוד פארם | Bina | http://goodpharm.binaprojects.com/MainIO_Hok.aspx |
| HAZI_HINAM | כל בו חצי חינם | MultiPageWeb | https://shop.hazi-hinam.co.il/Prices |
| HET_COHEN_NEW_SOURCE | ח. כהן | ApiWeb | https://laibcatalog.co.il/hcohen/index.html |
| KING_STORE | אלמשהדאוי קינג סטור | Bina | http://kingstore.binaprojects.com/MainIO_Hok.aspx |
| MAAYAN_2000 | מעיין אלפיים | Bina | http://maayan2000.binaprojects.com/MainIO_Hok.aspx |
| MAHSANI_ASHUK_NEW_SOURCE | מחסני השוק | ApiWeb | https://laibcatalog.co.il/mshuk/index.html |
| MESHMAT_YOSEF_1 | משנת יוסף | WebBase | https://list-files.w5871031-kt.workers.dev/ |
| NETIV_HASED | נתיב החסד | WebBase | http://141.226.203.152/ |
| QUIK | קוויק | PublishPrice | https://prices.quik.co.il/ |
| SHEFA_BARCART_ASHEM | שפע ברכת השם | Bina | http://shefabirkathashem.binaprojects.com/MainIO_Hok.aspx |
| SHUFERSAL | שופרסל | MultiPageWeb | https://prices.shufersal.co.il/ |
| SHUK_AHIR | שוק העיר | Bina | http://shuk-hayir.binaprojects.com/MainIO_Hok.aspx |
| SUPER_PHARM | סופר פארם | MultiPageWeb | http://prices.super-pharm.co.il/ |
| SUPER_SAPIR | סופר ספיר | Bina | http://supersapir.binaprojects.com/MainIO_Hok.aspx |
| VICTORY_NEW_SOURCE | ויקטורי | ApiWeb | https://laibcatalog.co.il/victory/index.html |
| WOLT | וולט | WebBase | https://wm-gateway.wolt.com/isr-prices/public/v1/index.html |
| YAYNO_BITAN_AND_CARREFOUR | יינות ביתן / קרפור | PublishPrice | https://prices.carrefour.co.il/ |
| ZOL_VEBEGADOL | זול ובגדול | Bina | http://zolvebegadol.binaprojects.com/MainIO_Hok.aspx |

### FTP (Cerberus) — `url.retail.publishedprices.co.il`

| ScraperFactory | Hebrew | FTP user | Path |
|---|---|---|---|
| COFIX | קופיקס | SuperCofixApp | / |
| DOR_ALON | דור אלון | doralon | / |
| FRESH_MARKET_AND_SUPER_DOSH | פרשמרקט | freshmarket | / |
| KESHET | קשת טעמים | Keshet | / |
| OSHER_AD | אושר עד | osherad | / |
| POLIZER | פוליצר | politzer | / |
| RAMI_LEVY | רמי לוי | RamiLevi | / |
| SALACH_DABACH | סאלח דבאח | SalachD | / |
| STOP_MARKET | סטופ מרקט | Stop_Market | / |
| SUPER_YUDA | סופר יודה | yuda_ho | /Yuda |
| TIV_TAAM | טיב טעם | TivTaam | / |
| YELLOW | יילו | Paz_bo | / |
| YOHANANOF | יוחננוף | yohananof | / |

Password is usually empty. Prefer `validate_ui_vs_scraper.py` over interactive `ftp`.

---

## Checklist

- [ ] Site reachable
- [ ] `ui_count` and `scraper_count` from the script
- [ ] `ui_not_in_scraper == 0` (PASS)
- [ ] Files recent (1–3 days) when investigating FAIL
- [ ] Chain id in filenames matches scraper `chain_id`
- [ ] Unstable / DNS-dead chains recorded (e.g. QUIK) — do not silently skip

## Common issues

| Symptom | Likely cause |
|---|---|
| `ui_not_in_scraper > 0` | Scraper filter/XPath/EDI bug |
| Site unreachable / DNS | Chain down; may be why scraper is stability-disabled |
| ApiWeb 400 on secondary EDI | Empty branches; primary EDI may still list all files |
| Paginated UI “page 1 only” | Always use full inventory (`const files` / all pages / FTP LIST) |
| gov.il 403 | Non-IL IP — use skill URLs or `dump_gov_il_links.py` fallback |
| Cerberus name mismatch in ad-hoc code | Yield order is `(name, url)`, not `(url, name)` |
