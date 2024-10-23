import datetime
import os
from il_supermarket_scarper import ScarpingTask, ScraperFactory, FileTypesFilters


def load_params():
    """load params from env variables with validation"""
    kwargs = {"suppress_exception": True, "lookup_in_db": True}

    # validate scrapers
    enabled_scrapers = os.getenv("ENABLED_SCRAPERS", None)
    if enabled_scrapers:
        enabled_scrapers = enabled_scrapers.split(",")

        not_valid = filter(
            lambda scraper: scraper not in ScraperFactory.all_scrapers_name(),
            enabled_scrapers,
        )
        if not_valid:
            raise ValueError(f"ENABLED_SCRAPERS contains invalid {not_valid}")

        kwargs["enabled_scrapers"] = enabled_scrapers

    # validate file types
    enabled_file_types = os.getenv("ENABLED_FILE_TYPES", None)
    if enabled_file_types:

        enabled_file_types = enabled_file_types.split(",")

        not_valid = filter(
            lambda f_types: f_types not in FileTypesFilters.all_types(),
            enabled_file_types,
        )
        if not_valid:
            raise ValueError(f"ENABLED_FILE_TYPES contains invalid {not_valid}")

        kwargs["enabled_file_types"] = enabled_file_types.split(",")

    # validate dump folder
    data_folder = os.getenv("DATA_FOLDER", None)
    if not data_folder:
        raise ValueError("DATA_FOLDER environment variable is required")
    kwargs["data_folder"] = data_folder

    # validate number of processes
    number_of_processes = os.getenv("NUMBER_OF_PROCESSES", None)
    if number_of_processes:
        try:
            kwargs["number_of_processes"] = int(number_of_processes)
        except ValueError:
            raise ValueError("NUMBER_OF_PROCESSES must be an integer")

    # validate limit
    limit = os.getenv("LIMIT", None)
    if limit:
        try:
            kwargs["limit"] = int(limit)
        except ValueError:
            raise ValueError(f"LIMIT must be an integer, but got {limit}")

    # validate today
    today = os.getenv("TODAY", None)
    if today:
        try:
            kwargs["when_date"] = datetime.datetime.strptime(today, "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError("TODAY must be in the format 'YYYY-MM-DD HH:MM'")
    return kwargs


if __name__ == "__main__":

    args = load_params()

    ScarpingTask(**args).start()
