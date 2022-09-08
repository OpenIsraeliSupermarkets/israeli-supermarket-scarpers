from il_supermarket_scarper.utils.status import get_status,get_all_listed_scarpers



def test_scrapers_are_updated():
    num_of_scarper_listed = len(get_all_listed_scarpers())
    num_of_scarper_on_gov_site = get_status()

    assert num_of_scarper_listed == num_of_scarper_on_gov_site


def test_all_chain_id_unqiue():
    all_chain_ids = list() 
    for scraper_init in get_all_listed_scarpers():
        all_chain_ids.extend(scraper_init().get_chain_id())

    assert len(list(set(all_chain_ids))) == len(all_chain_ids)