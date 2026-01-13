import os
import time
import tempfile

from il_supermarket_scarper.main import ScarpingTask
from il_supermarket_scarper.scrappers_factory import ScraperFactory


def test_main_with_limit():
    """test the main running with limit of 1 for each chain"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        expected = ScraperFactory.all_scrapers_name() + ["status"]
        scrapper_done = ScarpingTask(
            limit=1,
            output_configuration={
                "output_mode": "disk",
                "base_storage_path": tmpdirname,
            },
        ).start()

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
    with tempfile.TemporaryDirectory() as tmpdirname:
        scrapper_done = ScarpingTask(
            limit=1,
            enabled_scrapers=ScraperFactory.sample(n=1),
            output_configuration={
                "output_mode": "disk",
                "base_storage_path": tmpdirname,
            },
        ).start()
        assert (
            len(scrapper_done) == 1
            and len(os.listdir(tmpdirname)) == 2
            and len(os.listdir(scrapper_done[0])) == 1
        )


def test_main_with_one_scarper():
    """test size estmation mode"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        scrapper_done = ScarpingTask(
            limit=1,
            enabled_scrapers=ScraperFactory.sample(n=1),
            output_configuration={
                "output_mode": "disk",
                "base_storage_path": tmpdirname,
            },
        ).start()
        assert (
            len(scrapper_done) == 1
            and len(os.listdir(tmpdirname)) == 2
            and len(os.listdir(scrapper_done[0])) == 1
        )
