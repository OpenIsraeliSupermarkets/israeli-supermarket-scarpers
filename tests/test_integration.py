import datetime
from il_supermarket_scarper.utils.status import (
    get_status,
    get_status_date,
)
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import disable_when_outside_israel, DumpFolderNames


def test_scrapers_folders_match():
    """test the number of scrapers are the same as listed at the gov.il site"""
    scrapers_keys = ScraperFactory.all_scrapers_name()
    dump_keys = DumpFolderNames.all_folders_names()

    assert set(scrapers_keys) & set(dump_keys) == set(scrapers_keys)
    assert set(scrapers_keys) - set(dump_keys) == set()


@disable_when_outside_israel
def test_scrapers_are_updated():
    """test the number of scrapers are the same as listed at the gov.il site"""
    num_of_scarper_listed = len(ScraperFactory.all_listed_scrappers())
    num_of_scarper_on_gov_site = get_status()

    assert num_of_scarper_listed == num_of_scarper_on_gov_site


@disable_when_outside_israel
def test_update_date():
    """test date the site update"""
    date = get_status_date()
    assert date.date() == datetime.datetime(2024, 10, 6).date(), "gov il site changed"
