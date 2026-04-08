---
name: inspect-supermarket-sites
description: Visually inspect Israeli supermarket price-publication sites via the browser to verify files are available for download. Use when asked to check a supermarket site, verify scraper availability, inspect price files, browse the gov.il CPFTA page, or troubleshoot a specific scraper not finding files.
---

# Inspect Israeli Supermarket Sites

## Quick start

1. Open the browser to the gov.il registry page to find the chain's official portal link.
2. Navigate to the scraper's actual URL (from the table below) to verify files are listed.
3. For FTP-based scrapers (Cerberus engine), use a browser FTP URL or note that direct UI inspection is not possible.

---

## Gov.il Registry Page

**URL:** https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations

This page lists all chains subject to the Price Transparency Law. Each entry has a link to the chain's price-publication portal.

**Workflow:**
1. Navigate to the page.
2. Find the row matching the Hebrew company name (see table below).
3. Follow the link to the chain's portal and verify files are available.

> Note: The gov.il page may block non-Israeli IPs (returns 403). If blocked, go directly to the scraper URL.

---

## Scraper → URL Reference

### Web UI Scrapers (directly browsable)

| ScraperFactory Name | Hebrew Name | Engine | URL to visit |
|---|---|---|---|
| BAREKET | עוף והודו ברקת | Bina | http://superbareket.binaprojects.com/MainIO_Hok.aspx |
| CITY_MARKET_KIRYATGAT | סיטי מרקט | Bina | http://citymarketkiryatgat.binaprojects.com/MainIO_Hok.aspx |
| CITY_MARKET_SHOPS | סיטי מרקט | MultiPageWeb | http://www.citymarket-shops.co.il/ |
| GOOD_PHARM | גוד פארם | Bina | http://goodpharm.binaprojects.com/MainIO_Hok.aspx |
| HAZI_HINAM | כל בו חצי חינם | MultiPageWeb | https://shop.hazi-hinam.co.il/Prices |
| HET_COHEN | ח. כהן | Matrix | https://laibcatalog.co.il/NBCompetitionRegulations.aspx |
| KING_STORE | אלמשהדאוי קינג סטור | Bina | http://kingstore.binaprojects.com/MainIO_Hok.aspx |
| MAAYAN_2000 | מעיין אלפיים | Bina | http://maayan2000.binaprojects.com/MainIO_Hok.aspx |
| MAHSANI_ASHUK | מחסני השוק | Matrix | https://laibcatalog.co.il/NBCompetitionRegulations.aspx |
| MESHMAT_YOSEF_1 | משנת יוסף | WebBase | https://list-files.w5871031-kt.workers.dev/ |
| NETIV_HASED | נתיב החסד | WebBase | http://141.226.203.152/ |
| QUIK | קוויק | PublishPrice | https://prices.quik.co.il/ |
| SHEFA_BARCART_ASHEM | שפע ברכת השם | Bina | http://shefabirkathashem.binaprojects.com/MainIO_Hok.aspx |
| SHUFERSAL | שופרסל | MultiPageWeb | https://prices.shufersal.co.il/ |
| SHUK_AHIR | שוק העיר | Bina | http://shuk-hayir.binaprojects.com/MainIO_Hok.aspx |
| SUPER_PHARM | סופר פארם | MultiPageWeb | http://prices.super-pharm.co.il/ |
| SUPER_SAPIR | סופר ספיר | Bina | http://supersapir.binaprojects.com/MainIO_Hok.aspx |
| TIV_TAAM | טיב טעם | Cerberus/FTP | — see FTP section — |
| VICTORY | ויקטורי | Matrix | https://laibcatalog.co.il/NBCompetitionRegulations.aspx |
| VICTORY_NEW_SOURCE | ויקטורי | ApiWeb | https://laibcatalog.co.il |
| WOLT | וולט | WebBase | https://wm-gateway.wolt.com/isr-prices/public/v1/index.html |
| YAYNO_BITAN_AND_CARREFOUR | יינות ביתן / קרפור | PublishPrice | https://prices.carrefour.co.il/ |
| YELLOW | יילו | Cerberus/FTP | — see FTP section — |
| YOHANANOF | יוחננוף | Cerberus/FTP | — see FTP section — |
| ZOL_VEBEGADOL | זול ובגדול | Bina | http://zolvebegadol.binaprojects.com/MainIO_Hok.aspx |

### FTP-Based Scrapers (Cerberus engine)

These scrapers use FTP at `url.retail.publishedprices.co.il`. You cannot browse them via a web browser directly.

| ScraperFactory Name | Hebrew Name | FTP Username | FTP Path |
|---|---|---|---|
| COFIX | קופיקס | SuperCofixApp | / |
| DOR_ALON | דור אלון | doralon | / |
| FRESH_MARKET_AND_SUPER_DOSH | פרשמרקט / סופרדוש | freshmarket | / |
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

To inspect FTP scrapers, use a terminal: `ftp url.retail.publishedprices.co.il` then login with the username above (password is usually empty or matches the username).

---

## Engine-Specific Inspection Notes

### Bina (`binaprojects.com`)
- Page: `http://{prefix}.binaprojects.com/MainIO_Hok.aspx`
- Shows a table of files grouped by type (Store, Price, Promo, PriceFull, PromoFull).
- Healthy sign: rows visible in the table, files dated today or within the last few days.

### Matrix (`laibcatalog.co.il`)
- Page: `https://laibcatalog.co.il/NBCompetitionRegulations.aspx`
- Multiple chains share this page (HET_COHEN, MAHSANI_ASHUK, VICTORY).
- Filter by Hebrew chain name to see the correct chain's files.

### PublishPrice (`prices.{infix}.co.il`)
- Simple directory listing of `.gz` files.
- Healthy sign: files named with today's date in the filename.

### MultiPageWeb (Shufersal, Super Pharm, etc.)
- Each has its own web portal design.
- Look for a file listing or download section.

### WebBase (Netiv Hased, Meshnat Yosef, Wolt)
- Simple HTTP page listing files directly.

---

## Inspection Checklist

When checking a scraper site, verify:

- [ ] Site is reachable (no 403/404/timeout)
- [ ] Files are listed (not empty page)
- [ ] Files are recent (within last 1-3 days)
- [ ] File types present: Price, PriceFull, Promo, PromoFull, Store
- [ ] Chain ID in filenames matches the expected chain_id from `scrappers_factory.py`

## Common Issues

| Symptom | Likely cause |
|---|---|
| Empty file list | Scraper site down or chain not publishing |
| Files older than 3 days | Chain publishing irregularly |
| Wrong chain_id in files | Site_infix/url_prefix mismatch |
| FTP connection refused | Password changed or IP blocked |
| 403 on gov.il | Non-Israeli IP — use VPN or go directly to scraper URL |
