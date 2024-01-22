import datetime
from il_supermarket_scarper.utils.status import get_status, get_status_date
from il_supermarket_scarper.utils.connection import disable_when_outside_israel
from il_supermarket_scarper.scrappers_factory import ScraperFactory


@disable_when_outside_israel
def test_status():
    """check able to get the number of scrapers from gov.il"""
    num_of_scarpers = get_status()
    assert isinstance(num_of_scarpers, int)
    assert num_of_scarpers == len(ScraperFactory.all_listed_scrappers())


@disable_when_outside_israel
def test_status_date():
    """check able the get the date the gov.il site was updated"""
    date = get_status_date()
    assert isinstance(date, datetime.datetime)
    assert date == datetime.datetime(
        2024, 1, 14
    ), "gov il site changed, please check it out."
