import datetime
import time
from il_supermarket_scarper.utils.status import (
    get_status,
    get_status_date,
    get_statue_page,
    get_cpfta_retailer_hosts,
)
from il_supermarket_scarper.utils.connection import disable_when_outside_israel
from il_supermarket_scarper.utils.validation import show_text_diff, extract_main_content


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
    """make sure the main content (retailer list etc.) matches the cached page."""

    for _retries in range(3):
        cached = get_statue_page(extraction_type="all_text", source="cache")
        current = get_statue_page(extraction_type="all_text", source="gov.il")
        cached_main = extract_main_content(cached)
        current_main = extract_main_content(current)
        if current_main is not None and cached_main is not None:
            break
        time.sleep(2)
    assert (
        current_main is not None
    ), "gov.il page did not contain main content (possible block page)"
    assert cached_main is not None, "cached page did not contain main content"
    assert current_main == cached_main, show_text_diff(cached_main, current_main)


def test_cpfta_retailer_links_from_cached_html():
    """Parse retailer hosts from cached cpfta_prices_regulations HTML."""
    hosts = get_cpfta_retailer_hosts(source="cache")

    assert hosts, "cached cpfta HTML should contain retailer links"
    assert "app.netiv-hesed.com" in hosts
    assert "citymarketkiryatgat.binaprojects.com" in hosts
    assert "141.226.203.152" not in hosts
    assert "prices.quik.co.il" not in hosts
