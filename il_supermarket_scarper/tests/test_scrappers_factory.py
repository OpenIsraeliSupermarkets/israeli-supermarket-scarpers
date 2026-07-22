from il_supermarket_scarper import ScraperStability, ScraperFactory, datetime_in_tlv
from il_supermarket_scarper import scraper_stability as scraper_stability_module
from il_supermarket_scarper.utils import FileTypesFilters, _is_saturday_in_israel


def test_stable_scraper():
    """test sample stable scarper"""
    assert not ScraperStability.is_validate_scraper_found_no_files(
        ScraperFactory.VICTORY_NEW_SOURCE.name
    )


def test_city_market_kiryat_gat_is_active(monkeypatch):
    """City Market's Bina source should not be unconditionally disabled."""
    test_date = datetime_in_tlv(2024, 12, 12, 12, 0, 0)
    monkeypatch.setattr(scraper_stability_module, "_now", lambda: test_date)

    assert not ScraperStability.is_validate_scraper_found_no_files(
        ScraperFactory.CITY_MARKET_KIRYATGAT.name,
        files_types=[FileTypesFilters.STORE_FILE.name],
        when_date=test_date,
    )


# def test_after_date():
#     """test scrapers that failed after date"""
#     assert ScraperStability.is_validate_scraper_found_no_files(
#         ScraperFactory.CITY_MARKET_GIVATAYIM.name,
#         when_date=datetime_in_tlv(2024, 12, 12, 0, 0, 0),
#     )


def test_not_active(monkeypatch):
    """test grap between active and not"""
    test_date = datetime_in_tlv(2024, 12, 12, 12, 0, 0)
    monkeypatch.setattr(scraper_stability_module, "_now", lambda: test_date)
    all_listed = ScraperFactory.all_listed_scrappers()
    all_active = ScraperFactory.all_scrapers_name(when_date=test_date)

    # 'Quik' and 'Victory' are expected to fail
    expected_to_fail = 2
    if _is_saturday_in_israel(test_date):
        expected_to_fail += 1  # only 'NetivHased' should

    assert len(set(all_listed) - set(all_active)) == expected_to_fail
