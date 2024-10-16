from .scrapper_runner import MainScrapperRunner
from .utils.file_types import FileTypesFilters


class ScarpingTask:
    """scraping task encapsulated"""

    def __init__(
        self,
        size_estimation_mode=False,
        enabled_scrapers=None,
        limit=None,
        when_date=None,
        files_types=FileTypesFilters.all_types(),
        dump_folder_name=None,
        lookup_in_db=True,
        multiprocessing=5,
        suppress_exception=False,
    ):
        """define the runner"""
        self.runner = MainScrapperRunner(
            size_estimation_mode=size_estimation_mode,
            enabled_scrapers=enabled_scrapers,
            dump_folder_name=dump_folder_name,
            lookup_in_db=lookup_in_db,
            multiprocessing=multiprocessing,
        )
        self.dump_folder_name = dump_folder_name
        self.limit = limit
        self.files_types = files_types
        self.when_date = when_date
        self.suppress_exception = suppress_exception

    def get_dump_folder_name(self):
        """get the dump folder name"""
        return self.dump_folder_name

    def start(self):
        """run the scraping"""
        return self.runner.run(
            limit=self.limit,
            files_types=self.files_types,
            when_date=self.when_date,
            suppress_exception=self.suppress_exception,
        )
