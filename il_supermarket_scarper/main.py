import threading

from .scrapper_runner import MainScrapperRunner
from .utils.file_types import FileTypesFilters


class ScarpingTask:  # pylint: disable=too-many-instance-attributes
    """scraping task encapsulated"""

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
        """define the runner"""
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
        """run the scraping in a new thread"""
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
        """consume the scraping results"""
        return self.runner.consume_results()
    
    def join(self):
        """join the scraping thread"""
        if self._thread is not None and self._thread.is_alive():
            self._thread.join()
            return True
        raise RuntimeError("Scraping is not running")

    def stop(self):
        """stop the scraping"""
        self.runner.shutdown()
