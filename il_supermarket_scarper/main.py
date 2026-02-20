import threading

from .scrapper_runner import MainScrapperRunner
from .utils.file_types import FileTypesFilters


class ScarpingTask:  # pylint: disable=too-many-instance-attributes
    """
    Encapsulates a scraping task that can be run in a separate thread.

    This class provides a high-level interface for running scrapers with
    configurable options for file types, size limits, and output handling.
    The scraping runs in a background thread, allowing you to consume results
    as they become available.

    Args:
        enabled_scrapers (list, optional): List of scraper names to enable.
            If None, all available scrapers are enabled. Defaults to None.
        files_types (FileTypesFilters, optional): File types to download.
            Defaults to all file types.
        multiprocessing (int, optional): Number of parallel processes to use.
            Defaults to 5.
        min_size (int, optional): Minimum file size in bytes. Files smaller
            than this will be filtered out. Defaults to None (no minimum).
        max_size (int, optional): Maximum file size in bytes. Files larger
            than this will be filtered out. Defaults to None (no maximum).
        output_configuration (dict, optional): Configuration for file output.
            See MainScrapperRunner for details. Defaults to None.
        status_configuration (dict, optional): Configuration for status database.
            See MainScrapperRunner for details. Defaults to None.
        timeout_in_seconds (int, optional): Timeout for scraping operations
            in seconds. Defaults to 1800 (30 minutes).

    Example:
        Basic usage::

            from il_supermarket_scarper import ScarpingTask

            scraper = ScarpingTask()
            scraper.start()
            scraper.join()

        With specific scrapers and limits::

            from il_supermarket_scarper import ScarpingTask
            from il_supermarket_scarper.scrappers_factory import ScraperFactory

            scraper = ScarpingTask(
                enabled_scrapers=[ScraperFactory.WOLT],
                min_size=1000,
                max_size=10_000_000
            )
            scraper.start(limit=10)
            scraper.join()

        Consuming results::

            scraper = ScarpingTask()
            scraper.start()

            for result in scraper.consume():
                print(f"Downloaded: {result.file_name}")

            scraper.join()
    """

    def __init__(
        self,
        enabled_scrapers=None,
        files_types=FileTypesFilters.all_types(),
        multiprocessing=5,
        min_size=None,
        max_size=None,
        output_configuration=None,
        status_configuration=None,
        timeout_in_seconds=60 * 30,
    ):
        """
        Initialize the scraping task.

        Args:
            enabled_scrapers: List of scraper names to enable, or None for all.
            files_types: File types to download.
            multiprocessing: Number of parallel processes.
            min_size: Minimum file size in bytes.
            max_size: Maximum file size in bytes.
            output_configuration: File output configuration dictionary.
            status_configuration: Status database configuration dictionary.
            timeout_in_seconds: Timeout for scraping operations.
        """
        self.runner = MainScrapperRunner(
            enabled_scrapers=enabled_scrapers,
            timeout_in_seconds=timeout_in_seconds,
            multiprocessing=multiprocessing,
            output_configuration=output_configuration,
            status_configuration=status_configuration,
        )
        self.files_types = files_types
        self.min_size = min_size
        self.max_size = max_size
        self._thread = None

    def start(self, limit=None, when_date=None, single_pass=True):
        """
        Start the scraping task in a new background thread.

        Args:
            limit (int, optional): Maximum number of files to download.
                If None, downloads all available files. Defaults to None.
            when_date (datetime, optional): Date to download files from.
                If None, downloads latest files. Defaults to None.
            single_pass (bool, optional): If True, run once and stop.
                If False, continue running. Defaults to True.

        Returns:
            threading.Thread: The thread object running the scraping task.

        Raises:
            RuntimeError: If scraping is already running.

        Example::

            scraper = ScarpingTask()
            thread = scraper.start(limit=10)
            # Scraping is now running in background
        """
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Scraping is already running")

        def _run():
            """Internal function to run in thread"""
            self.runner.run(
                single_pass=single_pass,
                limit=limit,
                files_types=self.files_types,
                when_date=when_date,
                min_size=self.min_size,
                max_size=self.max_size,
            )

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        return self._thread

    def consume(self):
        """
        Consume scraping results as they become available.

        Returns:
            Generator[ScrapingResult]: Generator yielding ScrapingResult objects
                as files are downloaded and processed.

        Example::

            scraper = ScarpingTask()
            scraper.start()

            for result in scraper.consume():
                if result.extract_succefully:
                    print(f"Success: {result.file_name}")
                else:
                    print(f"Failed: {result.file_name} - {result.error}")

            scraper.join()
        """
        return self.runner.consume_results()

    def join(self):
        """
        Wait for the scraping thread to complete.

        Returns:
            bool: True if the thread was joined successfully.

        Raises:
            RuntimeError: If scraping is not running.

        Example::

            scraper = ScarpingTask()
            scraper.start()
            scraper.join()  # Wait for completion
        """
        if self._thread is not None and self._thread.is_alive():
            self._thread.join()
            return True
        raise RuntimeError("Scraping is not running")

    def stop(self):
        """
        Stop the scraping task and shutdown the runner.

        This method signals the scraper to stop and cleans up resources.
        It should be called when you want to terminate scraping before
        it completes naturally.

        Example::

            scraper = ScarpingTask()
            scraper.start()

            # ... do something ...

            scraper.stop()  # Stop scraping
        """
        self.runner.shutdown()
