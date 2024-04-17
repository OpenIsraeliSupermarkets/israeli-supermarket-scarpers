from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    for browser_type in [p.chromium, p.firefox, p.webkit]:
        browser = browser_type.launch()
        page = browser.new_page()
        page.goto('https://www.gov.il/he/pages/cpfta_prices_regulations')
        print(page.content())
        browser.close()