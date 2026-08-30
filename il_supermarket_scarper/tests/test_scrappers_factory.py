from il_supermarket_scarper import ScraperStability, ScraperFactory, datetime_in_tlv


def test_stable_scraper():
    """test sample stable scarper"""
    assert not ScraperStability.is_validate_scraper_found_no_files(
        ScraperFactory.VICTORY_NEW_SOURCE.name
    )


# def test_after_date():
#     """test scrapers that failed after date"""
#     assert ScraperStability.is_validate_scraper_found_no_files(
#         ScraperFactory.CITY_MARKET_GIVATAYIM.name,
#         when_date=datetime_in_tlv(2024, 12, 12, 0, 0, 0),
#     )


def test_not_active():
    """test grap between active and not"""
    test_date = datetime_in_tlv(2024, 12, 12, 0, 0, 0)
    all_listed = ScraperFactory.all_listed_scrappers()
    all_active = ScraperFactory.all_scrapers_name(when_date=test_date)

    # CityMarketKiratGat, NetivHased (site HTTP 500)
    expected_to_fail = 2

    assert len(set(all_listed) - set(all_active)) == expected_to_fail


def test_permanently_failing_scrapers_documented():
    """Ensure we know which scrapers are marked as permanently failing.

    This test serves as a canary: if a permanently-failing scraper starts
    returning files (site recovers or URL changes), the test suite logs a
    warning and this test documents which scrapers are in that state.

    When adding or removing a scraper from permanent-fail status:
    1. Update this test's expected set
    2. Review if the site actually recovered or moved to a new URL
    3. Update the scraper's URL if the site moved (check gov.il)
    4. Remove/adjust the unconditional `failire_valid()` override

    See: https://www.gov.il/he/pages/cpfta_prices_regulations for official URLs.
    """
    permanent_fail = set(ScraperStability.get_permanently_failing_scrapers())

    # Document the known permanently-failing scrapers and why:
    # - NETIV_HASED: Site moved from http://141.226.203.152/ to https://app.netiv-hesed.com/
    #   The hardcoded IP returns HTTP 500. URL needs update.
    # - CITY_MARKET_KIRYATGAT: Marked failing due to historical site issues.
    #   Site appears to be working now; `or True` should be removed.
    # - QUIK: Site DNS resolution fails (prices.quik.co.il).
    # - VICTORY: Moved to new source (VICTORY_NEW_SOURCE).
    expected_permanent_fail = {
        "NETIV_HASED",
        "CITY_MARKET_KIRYATGAT",
        "QUIK",
        "VICTORY",
    }

    assert permanent_fail == expected_permanent_fail, (
        f"Permanently-failing scrapers changed. "
        f"Added: {permanent_fail - expected_permanent_fail}, "
        f"Removed: {expected_permanent_fail - permanent_fail}. "
        f"If a scraper recovered, update its URL and remove its failire_valid override."
    )
