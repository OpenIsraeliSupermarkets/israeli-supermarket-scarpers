import datetime
import time
import asyncio
from multiprocessing import Pool, Manager

from .scrappers_factory import ScraperFactory
from .utils import (
    Logger,
    FilterState,
    _now,
)
from .engines.engine import Engine
from .utils.databases import (
    create_status_database_for_scraper,
    create_file_output_for_scraper,
)


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


async def _scrape_one(  # pylint: disable=too-many-locals
    chain_scrapper_class,
    limit=None,
    single_pass=False,
    files_types=None,
    file_name_regex=None,
    store_id=None,
    when_date=None,
    min_size=None,
    max_size=None,
    file_output=None,
    status_database=None,
    timeout_in_seconds=60 * 30,
    shutdown_flag=None,
    re_download=None,
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
    remaining_re_download = list(re_download or [])

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
        async for result in scraper.scrape(
            state=state,
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            file_name_regex=file_name_regex,
            filter_null=False,
            filter_zero=False,
            min_size=min_size,
            max_size=max_size,
            re_download=remaining_re_download,
        ):
            collected_now_count += 1
            if result:
                remaining_re_download = [
                    name
                    for name in remaining_re_download
                    if name not in result.file_name
                ]
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
        _sleep(timeout_in_seconds, shutdown_flag)

        # If we're continuing, log that we'll run again
        if not (shutdown_flag and shutdown_flag.value):
            Logger.info(f"[{chain_name}] Continuing to next run...")

    Logger.info(f"done scraping {chain_name}")
    if file_output is not None:
        await file_output.close()


def scrape_one_wrap(chain_scrapper_class, kwargs):
    """scrape one wrapper, each with its own event loop"""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_scrape_one(chain_scrapper_class, **kwargs))
    finally:
        loop.close()


class MainScrapperRunner:  # pylint: disable=too-many-instance-attributes
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
        # file_output (including queue handlers) and status DB must exist before run()
        # so downstream code can call consume() and attach consumers before start().
        self._file_outputs = {}
        self._status_databases = {}
        self._init_file_outputs()

    def _init_file_outputs(self):
        """Create per-scraper file output and status database (not tied to the process pool)."""
        self._file_outputs = {
            scraper_name: create_file_output_for_scraper(
                scraper_name, self.file_output_config
            )
            for scraper_name in self.enabled_scrapers
        }
        self._status_databases = {
            scraper_name: create_status_database_for_scraper(
                scraper_name, self.status_config
            )
            for scraper_name in self.enabled_scrapers
        }

    def run(
        self,
        limit=None,
        files_types=None,
        file_name_regex=None,
        when_date=False,
        min_size=None,
        max_size=None,
        single_pass=True,
        re_download=None,
    ):
        """run the scraper

        ``re_download`` maps a scraper name to file name substrings that must
        be downloaded again (see ``Engine.scrape``). Files outside
        ``files_types`` are not downloaded: the types pre-filter the request
        sent to the site.
        """
        re_download = re_download or {}
        Logger.info(f"Limit is {limit}")
        Logger.info(f"files_types is {files_types}")
        Logger.info(f"file_name_regex is {file_name_regex}")
        forced_counts = {name: len(files) for name, files in re_download.items()}
        Logger.info(f"re_download counts are {forced_counts}")
        Logger.info(f"Start scraping {self.enabled_scrapers}.")

        with Manager() as self._manager:
            self._shutdown_flag = self._manager.Value("b", False)
            tasks = [
                (
                    chain_scrapper_class,
                    {
                        "limit": limit,
                        "files_types": files_types,
                        "file_name_regex": file_name_regex,
                        "when_date": when_date,
                        "min_size": min_size,
                        "max_size": max_size,
                        "file_output": self._file_outputs[chain_scrapper_class],
                        "status_database": self._status_databases[chain_scrapper_class],
                        "single_pass": single_pass,
                        "timeout_in_seconds": self.timeout_in_seconds,
                        "shutdown_flag": self._shutdown_flag,
                        "re_download": list(
                            re_download.get(chain_scrapper_class) or []
                        ),
                    },
                )
                for chain_scrapper_class in self.enabled_scrapers
            ]
            with Pool(self.multiprocessing) as self._pool:
                async_result = self._pool.starmap_async(scrape_one_wrap, tasks)
                # Poll so we can terminate the pool from THIS thread when
                # shutdown is requested.  Calling pool.terminate() from a
                # different thread while starmap() blocks that same pool
                # object causes a deadlock in the pool's condition variable.
                while not async_result.ready():
                    if self._shutdown_flag.value:
                        Logger.info("Shutdown flag detected, terminating pool")
                        self._pool.terminate()
                        break
                    async_result.wait(timeout=1.0)
                result = async_result.get() if async_result.ready() else []
        self._manager = None
        self._shutdown_flag = None
        self._pool = None
        self._close_file_outputs()
        return result

    def _close_file_outputs(self):
        """Send end-of-stream sentinel to every queue output so consumers unblock."""
        for file_output in self._file_outputs.values():
            file_output.close_sync()

    def consume_results(self):
        """consume the scraping results - returns dict mapping scraper names
        to file_output and status_database"""
        return {
            scraper_name: self._file_outputs.get(scraper_name)
            for scraper_name in self._file_outputs
        }

    def shutdown(self):
        """Stop the scraping process.

        Sets the shutdown flag so the background thread's poll loop terminates
        the pool from within itself (avoids cross-thread pool deadlocks).
        Immediately closes all queue outputs so blocked consumers unblock.
        """
        Logger.info("Shutdown requested")
        if self._shutdown_flag is not None:
            try:
                self._shutdown_flag.value = True
            except (BrokenPipeError, ConnectionResetError, EOFError, OSError):
                # Manager connection already torn down - run() is finishing or finished.
                # This is expected when stop() is called after single_pass completion.
                pass
        # Close outputs NOW so any consumer blocked on queue.get() unblocks
        # immediately, even before the background thread exits.
        self._close_file_outputs()
