from il_supermarket_scarper import ScarpingTask, ScraperFactory
from il_supermarket_scarper.utils import _now, Logger

Logger.set_logging_level("INFO")

if __name__ == "__main__":
    scraper = ScarpingTask(
        dump_folder_name="dumps",
        lookup_in_db=False,
        multiprocessing=2,
        enabled_scrapers=[ScraperFactory.KING_STORE.name],
        # size_estimation_mode=True,  # download files,log size, delete files
        when_date=_now(),
    )
    scraper.start()
