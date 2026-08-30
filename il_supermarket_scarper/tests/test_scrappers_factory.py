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
    """Test scrapers that are listed in factory but disabled by stability rules.

    Note: ScraperStability may contain entries for scrapers that are no longer
    in ScraperFactory (e.g., QUIK, VICTORY were removed from factory but their
    stability rules remain). Only scrapers IN the factory can be "not active".
    """
    test_date = datetime_in_tlv(2024, 12, 12, 0, 0, 0)
    all_listed = ScraperFactory.all_listed_scrappers()
    all_active = ScraperFactory.all_scrapers_name(when_date=test_date)

    # Get permanently failing scrapers that are also in the factory
    permanent_fail = set(ScraperStability.get_permanently_failing_scrapers())
    factory_scrapers = set(all_listed)
    expected_not_active = permanent_fail & factory_scrapers

    actual_not_active = set(all_listed) - set(all_active)

    assert actual_not_active == expected_not_active, (
        f"Not-active scrapers mismatch. "
        f"Expected: {expected_not_active}, "
        f"Actual: {actual_not_active}. "
        f"Difference: {actual_not_active.symmetric_difference(expected_not_active)}"
    )


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
    #   (UNSTABLE - on gov.il, URL needs update)
    # - QUIK: Site DNS resolution fails (prices.quik.co.il).
    #   (UNSTABLE - on gov.il, retailer's site is down)
    # - VICTORY: Moved to new source (VICTORY_NEW_SOURCE).
    #   (DEPRECATED - replaced by new scraper, not expected on gov.il)
    expected_permanent_fail = {
        "NETIV_HASED",
        "QUIK",
        "VICTORY",
    }

    assert permanent_fail == expected_permanent_fail, (
        f"Permanently-failing scrapers changed. "
        f"Added: {permanent_fail - expected_permanent_fail}, "
        f"Removed: {expected_permanent_fail - permanent_fail}. "
        f"If a scraper recovered, update its URL and remove its failire_valid override."
    )


def test_deprecated_vs_unstable_scrapers():
    """Verify deprecated scrapers are distinct from unstable ones.

    - Deprecated: Retailers no longer on gov.il (e.g., VICTORY replaced by VICTORY_NEW_SOURCE)
    - Unstable: Retailers still on gov.il but scraper is broken (need fixing)

    Unstable scrapers should have their URLs validated against gov.il.
    If gov.il shows a different URL, update the scraper.
    """
    deprecated = set(ScraperStability.get_deprecated_scrapers())
    unstable = set(ScraperStability.get_unstable_scrapers())

    # Deprecated scrapers - OK to not work, not expected on gov.il
    expected_deprecated = {"VICTORY"}
    assert deprecated == expected_deprecated, (
        f"Deprecated scrapers changed. "
        f"Added: {deprecated - expected_deprecated}, "
        f"Removed: {expected_deprecated - deprecated}."
    )

    # Unstable scrapers - still on gov.il, need attention
    expected_unstable = {"NETIV_HASED", "QUIK"}
    assert unstable == expected_unstable, (
        f"Unstable scrapers changed. "
        f"Added: {unstable - expected_unstable}, "
        f"Removed: {expected_unstable - unstable}."
    )


def test_unstable_scrapers_on_gov_il():
    """Verify unstable scrapers are validated against gov.il listings.

    If a scraper is marked as unstable (expected to fail) but is still listed
    on gov.il, we need to investigate and fix it. This test documents which
    scrapers need attention.

    For scrapers with URL drift (our URL differs from gov.il):
    - Update the scraper's URL to match gov.il
    - Remove the failire_valid() override once working
    """
    validation = ScraperStability.validate_against_gov_il()

    # All unstable scrapers that are on gov.il need attention
    unstable_on_gov_il = set(validation["unstable_on_gov_il"])
    url_drift = validation["url_drift"]

    # Document expected state - these need fixing but are known issues
    expected_unstable_on_gov_il = {"NETIV_HASED", "QUIK"}
    assert unstable_on_gov_il == expected_unstable_on_gov_il, (
        f"Unstable scrapers on gov.il changed. "
        f"New scrapers needing attention: {unstable_on_gov_il - expected_unstable_on_gov_il}, "
        f"Resolved: {expected_unstable_on_gov_il - unstable_on_gov_il}."
    )

    # Document known URL drift - these explicitly need URL updates
    expected_url_drift = {"NETIV_HASED"}
    assert set(url_drift.keys()) == expected_url_drift, (
        f"URL drift detected. "
        f"New drift: {set(url_drift.keys()) - expected_url_drift}, "
        f"Resolved: {expected_url_drift - set(url_drift.keys())}. "
        f"Update scraper URLs to match gov.il listings."
    )

    # Verify NETIV_HASED URL drift is documented
    if "NETIV_HASED" in url_drift:
        assert url_drift["NETIV_HASED"]["scraper_expected"] == "https://app.netiv-hesed.com/", (
            "NETIV_HASED expected URL should be https://app.netiv-hesed.com/"
        )
