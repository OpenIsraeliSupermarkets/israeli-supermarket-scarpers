from il_supermarket_scarper import ScraperStability, ScraperFactory, datetime_in_tlv
from il_supermarket_scarper.scraper_stability import ScraperKind
from il_supermarket_scarper.utils.status import get_cpfta_retailer_hosts


def test_stable_scraper():
    """test sample stable scarper"""
    assert not ScraperStability.is_validate_scraper_found_no_files(
        ScraperFactory.VICTORY_NEW_SOURCE.name
    )


def test_not_active():
    """Always-failing factory scrapers are skipped in production (all_active)."""
    test_date = datetime_in_tlv(2024, 12, 12, 0, 0, 0)
    all_listed = set(ScraperFactory.all_listed_scrappers())
    all_active = set(ScraperFactory.all_scrapers_name(when_date=test_date))

    expected_not_active = (
        set(ScraperStability.get_always_failing_scrapers()) & all_listed
    )
    actual_not_active = all_listed - all_active

    assert actual_not_active == expected_not_active, (
        f"Not-active scrapers mismatch. "
        f"Expected: {expected_not_active}, "
        f"Actual: {actual_not_active}."
    )


def test_scraper_kinds():
    """Three kinds: edge-case, always-failing (still on gov.il), deprecated."""
    assert set(ScraperStability.get_deprecated_scrapers()) == {"QUIK", "VICTORY"}
    assert set(ScraperStability.get_always_failing_scrapers()) == {
        "CITY_MARKET_KIRYATGAT",
        "NETIV_HASED",
    }

    factory_names = set(ScraperFactory.all_listed_scrappers())
    for name in ScraperStability.get_deprecated_scrapers():
        assert name not in factory_names, f"deprecated {name} must not be in factory"

    for name in ScraperStability.get_always_failing_scrapers():
        assert name in factory_names, f"always-failing {name} must stay in factory"
        assert ScraperStability.kind_of(name) is ScraperKind.ALWAYS_FAILING


def test_always_failing_urls_match_gov_il():
    """Always-failing scrapers must still be listed in the cached gov.il HTML.

    If this fails, update the scraper class URL to match cpfta_prices_regulations
    (or mark the scraper deprecated if it was removed from gov.il).
    """
    drift = ScraperStability.always_failing_url_drift()
    assert not drift, (
        "Always-failing scraper URL is not in cpfta_prices_regulations. "
        f"Update scraper configuration: {drift}"
    )

    gov_il_hosts = get_cpfta_retailer_hosts()
    assert "app.netiv-hesed.com" in gov_il_hosts
    assert "citymarketkiryatgat.binaprojects.com" in gov_il_hosts
    assert "prices.quik.co.il" not in gov_il_hosts
