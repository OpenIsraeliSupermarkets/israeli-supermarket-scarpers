from .scrapper_runner import MainScrapperRunner
from .utils.file_types import FileTypesFilters


class ScarpingTask:  # pylint: disable=too-many-instance-attributes
    """scraping task encapsulated"""

    def __init__(
        self,
        size_estimation_mode=False,
        enabled_scrapers=None,
        files_types=FileTypesFilters.all_types(),
        multiprocessing=5,
        min_size=None,
        max_size=None,
        output_configuration=None,
        status_configuration=None,
    ):
        """define the runner"""
        self.runner = MainScrapperRunner(
            size_estimation_mode=size_estimation_mode,
            enabled_scrapers=enabled_scrapers,
            multiprocessing=multiprocessing,
            output_configuration=output_configuration,
            status_configuration=status_configuration,
        )
        self.files_types = files_types
        self.min_size = min_size
        self.max_size = max_size

    def start(self, limit, when_date):
        """run the scraping"""
        return self.runner.run(
            limit=limit,
            files_types=self.files_types,
            when_date=when_date,
            min_size=self.min_size,
            max_size=self.max_size,
        )
