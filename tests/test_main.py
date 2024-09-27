import os
import time
import tempfile

from il_supermarket_scarper.main import ScarpingTask
from il_supermarket_scarper.scrappers_factory import ScraperFactory


def test_main_with_limit():
    """test the main running with limit of 1 for each chain"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        expected = ScraperFactory.all_scrapers_name() + ["status"]
        scrapper_done = ScarpingTask(limit=1, dump_folder_name=tmpdirname).start()

        folders_from_scraper = list(map(lambda x: x.split("/")[-1], scrapper_done)) + [
            "status"
        ]
        time.sleep(5)
        folders_in_dump_folder = os.listdir(tmpdirname)
        folders_in_dump_folder = [
            name for name in folders_in_dump_folder if not name.startswith(".")
        ]
        assert len(folders_in_dump_folder) == len(expected)
        assert sorted(folders_from_scraper) == sorted(folders_in_dump_folder)


def test_main_with_one_scarper():
    """the limit only for enabled scarpers"""
    scrapper_done = ScarpingTask(
        limit=1, enabled_scrapers=ScraperFactory.sample(n=1)
    ).start()
    assert len(scrapper_done) == 1


def test_main_with_size_estimation_mode():
    """test size estmation mode"""
    scrapper_done = ScarpingTask(
        limit=1, size_estimation_mode=True, enabled_scrapers=ScraperFactory.sample(n=1)
    ).start()
    assert len(scrapper_done) == 1
