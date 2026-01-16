import os
import time
import tempfile

from il_supermarket_scarper.main import ScarpingTask
from il_supermarket_scarper.scrappers_factory import ScraperFactory


def test_main_with_limit():
    """test the main running with limit of 1 for each chain"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        scrapers = [ScraperFactory.BAREKET.name]
        expected = scrapers 
        scrapper_done = ScarpingTask(
            enabled_scrapers=scrapers,
            output_configuration={
                "output_mode": "disk",
                "base_storage_path": tmpdirname,
            },
            status_configuration={
                "database_type": "json",
                "base_path": os.path.join(tmpdirname, "status"),
            },
        )
        scrapper_done.start(limit=1, when_date=None, single_pass=True)
        scrapper_done.wait()

        list_of_status_files = os.listdir(os.path.join(tmpdirname, "status"))
        assert len(list_of_status_files) == len(expected)
        assert sorted(map(lambda x: x.lower(), list_of_status_files)) == sorted(map(lambda x: x.lower() + ".json", expected))

        time.sleep(5)
        for scraper_name, file_output in scrapper_done.consume().items():
            folders_in_dump_folder = os.listdir(file_output.get_storage_path())
            assert len(folders_in_dump_folder) == 1
            assert scraper_name.lower() in file_output.get_storage_path().lower()
 

def test_main_with_one_scarper():
    """the limit only for enabled scarpers"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        scrapper_done = ScarpingTask(
            enabled_scrapers=ScraperFactory.sample(n=1),
            output_configuration={
                "output_mode": "disk",
                "base_storage_path": tmpdirname,
            },
        )
        scrapper_done.start(limit=1, when_date=None, single_pass=True)
        scrapper_done.wait()
        assert (
            len(scrapper_done) == 1
            and len(os.listdir(tmpdirname)) == 2
            and len(os.listdir(scrapper_done[0])) == 1
        )


def test_main_with_one_scarper():
    """test size estmation mode"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        scrapper_done = ScarpingTask( 
            enabled_scrapers=ScraperFactory.sample(n=1),
            output_configuration={
                "output_mode": "disk",
                "base_storage_path": tmpdirname,
            },
        )
        scrapper_done.start(limit=1, when_date=None, single_pass=True)
        scrapper_done.wait()
        assert (
            len(scrapper_done) == 1
            and len(os.listdir(tmpdirname)) == 2
            and len(os.listdir(scrapper_done[0])) == 1
        )
