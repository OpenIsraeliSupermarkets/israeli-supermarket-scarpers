from il_supermarket_scarper import ScarpingTask, ScraperFactory
from il_supermarket_scarper.utils import _now, Logger

Logger.set_logging_level("INFO")

if __name__ == "__main__":
    scraper = ScarpingTask(
        output_configuration={"output_mode": "disk", "base_storage_path": "dumps"},
        status_configuration={"database_type": "json", "base_path": "status_logs"},
        multiprocessing=2,
        limit=1,
        enabled_scrapers=[ScraperFactory.BAREKET.name],
        when_date=_now(),
    )
    scraper.start()
