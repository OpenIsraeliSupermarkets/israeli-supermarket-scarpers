from il_supermarket_scarper.utils.status import get_status
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils.connection import disable_when_outside_israel


@disable_when_outside_israel
def test_scrapers_are_updated():
    """test the number of scrapers are the same as listed at the gov.il site"""
    num_of_scarper_listed = len(ScraperFactory.all_scrapers_name())
    num_of_scarper_on_gov_site = get_status()

    assert num_of_scarper_listed == num_of_scarper_on_gov_site


def test_all_chain_id_unqiue():
    """test all scrapers are working on diffrent chain"""
    all_chain_ids = []
    for scraper_init in ScraperFactory.all_scrapers():
        all_chain_ids.extend(scraper_init().get_chain_id())

    assert len(list(set(all_chain_ids))) == len(all_chain_ids)
