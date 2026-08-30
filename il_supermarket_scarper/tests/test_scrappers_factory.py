from il_supermarket_scarper import ScraperStability, ScraperFactory, datetime_in_tlv
from il_supermarket_scarper.scraper_stability import ScraperKind
from il_supermarket_scarper.utils.status import get_cpfta_retailer_hosts
import tempfile

from il_supermarket_scarper.utils.file_output import DiskFileOutput


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


def test_always_failing_login_details_match_gov_il():
    """Always-failing scrapers must still be listed in the cached gov.il HTML."""
    for name in ScraperStability.get_always_failing_scrapers():
        scraper_cls = ScraperFactory.get(name)
        with tempfile.TemporaryDirectory() as tmp:
            instance = scraper_cls(file_output=DiskFileOutput(storage_path=tmp))
            login_details = instance.get_login_details()
            assert get_cpfta_retailer_hosts(login_details)
   