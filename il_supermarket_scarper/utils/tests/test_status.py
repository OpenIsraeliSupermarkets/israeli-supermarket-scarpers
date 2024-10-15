import datetime

from il_supermarket_scarper.utils.status import (
    get_status,
    get_status_date,
    get_statue_page,
)
from il_supermarket_scarper.utils.connection import disable_when_outside_israel
from il_supermarket_scarper.utils.validation import show_text_diff


@disable_when_outside_israel
def test_status():
    """check able to get the number of scrapers from gov.il"""
    num_of_scarpers = get_status()
    assert isinstance(num_of_scarpers, int)


@disable_when_outside_israel
def test_status_date():
    """check able the get the date the gov.il site was updated"""
    date = get_status_date()
    assert isinstance(date, datetime.datetime)


@disable_when_outside_israel
def test_page_complete_diff():
    """make sure the page content is the same as the cached page"""
    cached = get_statue_page(extraction_type="all_text", source="cache")
    current = get_statue_page(extraction_type="all_text", source="gov.il")
    assert current == cached, show_text_diff(cached, current)
