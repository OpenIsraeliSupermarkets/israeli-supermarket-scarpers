import os
import shutil
import time
from il_supermarket_scarper.main import ScarpingTask
from il_supermarket_scarper.scrappers_factory import ScraperFactory


def test_main_with_limit():
    """test the main running with limit of 1 for each chain"""
    expected = ScraperFactory.all_scrapers_name()
    output_folder = "test_dump"
    scrapper_done = ScarpingTask(limit=1, dump_folder_name=output_folder).start()

    folders_from_scraper = list(map(lambda x: x.split("/")[1], scrapper_done))

    time.sleep(5)
    folders_in_dump_folder = os.listdir(output_folder)
    folders_in_dump_folder = [
        name for name in folders_in_dump_folder if not name.startswith(".")
    ]
    assert len(folders_in_dump_folder) == len(expected)
    assert sorted(folders_from_scraper) == sorted(folders_in_dump_folder)

    shutil.rmtree(output_folder)


def test_main_with_one_scarper():
    """the limit only for enabled scarpers"""
    scrapper_done = ScarpingTask(
        limit=1, enabled_scrapers=[ScraperFactory.DOR_ALON]
    ).start()
    assert "dor" in scrapper_done[0].lower() and "alon" in scrapper_done[0].lower()
    assert len(scrapper_done) == 1


def test_main_with_size_estimation_mode():
    """test size estmation mode"""
    scrapper_done = ScarpingTask(
        limit=1, size_estimation_mode=True, enabled_scrapers=[ScraperFactory.DOR_ALON]
    ).start()
    assert len(scrapper_done) == 1
