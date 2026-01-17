import os
import datetime
import time
import asyncio
from multiprocessing import Pool, Manager

from .scrappers_factory import ScraperFactory
from .utils import (
    Logger,
    DumpFolderNames,
    DiskFileOutput,
    QueueFileOutput,
    InMemoryQueueHandler,
    FilterState,
    _now,
)
from .engines.engine import Engine


def _should_exit(
    state, limit, single_pass, initial_when_date, collected_now_count, chain_name
):
    """check if the scraping should exit"""
    should_exit = False
    exit_reason = None

    # Condition 1: Limit reached
    if limit is not None and state.file_pass_limit >= limit:
        should_exit = True
        exit_reason = f"limit reached ({state.file_pass_limit}/{limit})"

    # Condition 2: Single pass completed
    elif single_pass:
        should_exit = True
        exit_reason = "single pass completed"

    # Condition 3: when_date provided, day has passed, and no new files found
    elif initial_when_date is not None and isinstance(
        initial_when_date, datetime.datetime
    ):
        current_date = _now().date()
        when_date_date = initial_when_date.date()

        # Check if the day has passed
        if current_date > when_date_date:
            # If no files were found in this run, exit
            if collected_now_count == 0:
                should_exit = True
                exit_reason = (
                    f"day has passed ({when_date_date} -> {current_date}) "
                    f"and no additional files found"
                )
            else:
                # Day passed but files were found, continue
                Logger.info(
                    f"[{chain_name}] Day has passed but found {collected_now_count} "
                    f"files, continuing..."
                )
    return should_exit, exit_reason


def _sleep(timeout_in_seconds, shutdown_flag):
    """Sleep in smaller chunks to check shutdown flag more frequently"""
    Logger.info(f"Sleeping for {timeout_in_seconds} seconds")
    sleep_chunk = min(1.0, timeout_in_seconds)
    slept = 0
    while slept < timeout_in_seconds and not (shutdown_flag and shutdown_flag.value):
        time.sleep(sleep_chunk)
        slept += sleep_chunk
        if slept + sleep_chunk > timeout_in_seconds:
            sleep_chunk = timeout_in_seconds - slept


async def _scrape_one(
    chain_scrapper_class,
    limit=None,
    single_pass=False,
    files_types=None,
    store_id=None,
    when_date=None,
    min_size=None,
    max_size=None,
    file_output=None,
    status_database=None,
    timeout_in_seconds=60 * 30,
    shutdown_flag=None,
):
    """scrape one"""
    chain_scrapper_constractor = ScraperFactory.get(chain_scrapper_class)
    Logger.info(f"Starting scrapper {chain_scrapper_constractor}")

    # Create scraper with both file_output and status_database
    scraper: Engine = chain_scrapper_constractor(
        file_output=file_output, status_database=status_database
    )

    chain_name: str = scraper.get_chain_name()

    Logger.info(f"scraping {chain_name}")

    # Track state across multiple runs
    state = FilterState()
    run_count = 0
    initial_when_date = when_date

    # Loop until one of the exit conditions is met
    while True:
        # Check for shutdown flag
        if shutdown_flag and shutdown_flag.value:
            Logger.info(f"[{chain_name}] Shutdown requested, exiting loop")
            break

        run_count += 1
        Logger.info(f"[{chain_name}] Starting run #{run_count}")

        # Run the scraper
        collected_now_count = 0
        async for _ in scraper.scrape(
            state=state,
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            files_names_to_scrape=None,
            filter_null=False,
            filter_zero=False,
            min_size=min_size,
            max_size=max_size,
        ):
            collected_now_count += 1
            # Check for shutdown during scraping
            if shutdown_flag and shutdown_flag.value:
                Logger.info(f"[{chain_name}] Shutdown requested during scraping")
                break

        Logger.info(
            f"[{chain_name}] Run #{run_count} completed. "
            f"Files found: {collected_now_count}, "
            f"Total files: {state.file_pass_limit}"
        )

        # Check for shutdown flag again
        if shutdown_flag and shutdown_flag.value:
            Logger.info(f"[{chain_name}] Shutdown requested, exiting loop")
            break

        # Check exit conditions
        should_exit, exit_reason = _should_exit(
            state,
            limit,
            single_pass,
            initial_when_date,
            collected_now_count,
            chain_name,
        )

        if should_exit:
            Logger.info(f"[{chain_name}] Exiting loop: {exit_reason}")
            break
        else:
            _sleep(timeout_in_seconds, shutdown_flag)

        # If we're continuing, log that we'll run again
        if not (shutdown_flag and shutdown_flag.value):
            Logger.info(f"[{chain_name}] Continuing to next run...")

    Logger.info(f"done scraping {chain_name}")


def scrape_one_wrap(chainScrapperClass, kwargs):
    """scrape one wrapper, each with its own event loop"""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_scrape_one(chainScrapperClass, **kwargs))
    finally:
        loop.close()


class MainScrapperRunner:
    """a main scraper to execute all scraping"""

    def __init__(
        self,
        enabled_scrapers=None,
        timeout_in_seconds=60 * 30,
        multiprocessing=5,
        output_configuration=None,
        status_configuration=None,
    ):
        assert isinstance(enabled_scrapers, list) or enabled_scrapers is None

        if not enabled_scrapers:
            enabled_scrapers = ScraperFactory.all_scrapers_name()

        self.enabled_scrapers = enabled_scrapers
        Logger.info(f"Enabled scrapers: {self.enabled_scrapers}")
        self.multiprocessing = multiprocessing
        self.timeout_in_seconds = timeout_in_seconds
        self.file_output_config = output_configuration or {
            "output_mode": "disk",
            "base_storage_path": "dumps",
        }
        self.status_config = status_configuration or {
            "database_type": "json",
            "base_path": "dumps/status",
        }
        self._manager = None
        self._shutdown_flag = None
        self._pool = None

        # Create file_output and status_database objects during init
        # so they can be consumed before/during scraping
        self._file_outputs = {}
        self._status_databases = {}
        for scraper_name in self.enabled_scrapers:
            self._file_outputs[scraper_name] = self._create_file_output_for_scraper(
                scraper_name, self.file_output_config
            )
            self._status_databases[scraper_name] = self._create_status_database_for_scraper(
                scraper_name, self.status_config
            )

    def _create_status_database_for_scraper(self, scraper_name, config):
        """Create a status database instance for a specific scraper based on config."""
        from .utils.databases import create_status_database_for_scraper

        return create_status_database_for_scraper(scraper_name, config)

    def _create_file_output_for_scraper(self, scraper_name, config):
        """
        Create a file_output instance for a specific scraper based on config.

        Args:
            scraper_name: Name of the scraper
            config: Configuration dictionary
        """
        target_folder = DumpFolderNames[scraper_name].value

        # Use default config if None
        if config is None:
            config = {
                "output_mode": "disk",
                "base_storage_path": "dumps",
            }

        if config.get("output_mode") == "disk":
            # Disk output mode
            base_path = config.get("base_storage_path", "dumps")
            return DiskFileOutput(storage_path=os.path.join(base_path, target_folder))

        elif config.get("output_mode") == "queue":
            # Queue output mode
            queue_type = config.get("queue_type", "memory")

            if queue_type == "memory":
                return QueueFileOutput(
                    InMemoryQueueHandler(queue_name=target_folder)
                )


    def run(
        self,
        limit=None,
        files_types=None,
        when_date=False,
        min_size=None,
        max_size=None,
        single_pass=True,
    ):
        """run the scraper"""
        self._manager = Manager()
        self._shutdown_flag = self._manager.Value("b", False)

        Logger.info(f"Limit is {limit}")
        Logger.info(f"files_types is {files_types}")
        Logger.info(f"Start scraping {self.enabled_scrapers}.")

        self._pool = Pool(self.multiprocessing)
        try:
            result = self._pool.starmap(
                scrape_one_wrap,
                [
                    (
                        chainScrapperClass,
                        {
                            "limit": limit,
                            "files_types": files_types,
                            "when_date": when_date,
                            "min_size": min_size,
                            "max_size": max_size,
                            "file_output": self._file_outputs[chainScrapperClass],
                            "status_database": self._status_databases[
                                chainScrapperClass
                            ],
                            "single_pass": single_pass,
                            "timeout_in_seconds": self.timeout_in_seconds,
                            "shutdown_flag": self._shutdown_flag,
                        },
                    )
                    for chainScrapperClass in self.enabled_scrapers
                ],
            )

            Logger.info("Done scraping all supermarkets.")



            return result
        finally:
            self._pool.close()
            self._pool.join()
            self._pool = None
            if self._manager:
                self._manager.shutdown()
                self._manager = None
                self._shutdown_flag = None

    def consume_results(self):
        """consume the scraping results - returns dict mapping scraper names to file_output and status_database"""
        return {
            scraper_name: self._file_outputs.get(scraper_name)
            for scraper_name in self._file_outputs.keys()
        }

    def shutdown(self):
        """Stop the scraping process"""
        Logger.info("Shutdown requested")
        if self._shutdown_flag is not None:
            self._shutdown_flag.value = True
        if self._pool is not None:
            Logger.info("Terminating pool processes")
            self._pool.terminate()
            self._pool.join()
            self._pool = None
