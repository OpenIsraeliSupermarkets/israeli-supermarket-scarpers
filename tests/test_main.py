import os
import time
import tempfile
import asyncio

from il_supermarket_scarper.main import ScarpingTask
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils.file_output import QueueFileOutput

def test_main_to_disk():
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


def test_main_to_memory_queue():
    """test the main running with limit of 1 for each chain using in-memory queue"""
    async def run_test():
        with tempfile.TemporaryDirectory() as tmpdirname:
            scrapers = [ScraperFactory.BAREKET.name]
            expected = scrapers 
            scrapper_done = ScarpingTask(
                enabled_scrapers=scrapers,
                output_configuration={
                    "output_mode": "queue",
                    "queue_type": "memory",
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

            for scraper_name, file_output in scrapper_done.consume().items():
                # For queue output, check messages in the queue handler
                count = 0
                assert isinstance(file_output, QueueFileOutput)
                async for message in file_output.queue_handler.get_all_messages():
                    count += 1
                    # Verify message structure
                    assert "file_name" in message
                    assert "file_content" in message
                    assert "file_link" in message
                    assert "metadata" in message

                assert count == 1
                assert scraper_name.lower() in file_output.queue_handler.get_queue_name().lower()

            scrapper_done.stop()
    
    asyncio.run(run_test())