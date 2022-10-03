from .scrapper_runner import MainScrapperRunner
from .utils.file_types import FileTypesFilters

class ScarpingTask:

    def start(self,size_estimation_mode=False,enabled_scrapers=None,limit=None,files_types=FileTypesFilters.all_types(),dump_folder_name=None):
        runner = MainScrapperRunner(size_estimation_mode=size_estimation_mode,enabled_scrapers=enabled_scrapers,dump_folder_name=dump_folder_name)
        return runner.run(limit=limit,files_types=files_types)


if __name__ == '__main__':
    ScarpingTask().start()
