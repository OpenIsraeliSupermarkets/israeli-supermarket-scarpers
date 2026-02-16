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
        valid_scrapers = ScraperFactory.all_scrapers_name()
        not_valid = set(enabled_scrapers) - set(valid_scrapers)

        if not_valid:
            raise ValueError(f"ENABLED_SCRAPERS contains invalid {list(not_valid)}")

        kwargs["enabled_scrapers"] = enabled_scrapers

    # validate file types
    enabled_file_types = os.getenv("ENABLED_FILE_TYPES", None)
    if enabled_file_types:

        enabled_file_types = enabled_file_types.split(",")
        valid_types = FileTypesFilters.all_types()
        not_valid = set(enabled_file_types) - set(valid_types)

        if not_valid:
            raise ValueError(f"ENABLED_FILE_TYPES contains invalid {list(not_valid)}")

        kwargs["files_types"] = enabled_file_types

    # validate number of processes
    number_of_processes = os.getenv("NUMBER_OF_PROCESSES", None)
    if number_of_processes:
        try:
            kwargs["multiprocessing"] = int(number_of_processes)
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
