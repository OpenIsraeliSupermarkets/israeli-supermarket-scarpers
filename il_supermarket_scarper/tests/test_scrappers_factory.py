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

    # CityMarketKiratGat, Quik, NetivHased (site HTTP 500)
    expected_to_fail = 3

    assert len(set(all_listed) - set(all_active)) == expected_to_fail
