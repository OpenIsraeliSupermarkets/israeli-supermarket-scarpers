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

        not_valid = list(
            filter(
                lambda scraper: scraper not in ScraperFactory.all_scrapers_name(),
                enabled_scrapers,
            )
        )
        if not_valid:
            raise ValueError(f"ENABLED_SCRAPERS contains invalid {not_valid}")

        kwargs["enabled_scrapers"] = enabled_scrapers

    # validate file types
    enabled_file_types = os.getenv("ENABLED_FILE_TYPES", None)
    if enabled_file_types:

        enabled_file_types = enabled_file_types.split(",")

        not_valid = list(
            filter(
                lambda f_types: f_types not in FileTypesFilters.all_types(),
                enabled_file_types,
            )
        )
        if not_valid:
            raise ValueError(f"ENABLED_FILE_TYPES contains invalid {not_valid}")

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

    # validate output mode (disk or queue)
    output_mode = os.getenv("OUTPUT_MODE", "disk").lower()
    if output_mode not in ["disk", "queue"]:
        raise ValueError(
            f"OUTPUT_MODE must be 'disk' or 'queue', but got {output_mode}"
        )

    # Pass output configuration instead of file_output instances
    # Each scraper will create its own file_output based on its folder name
    output_configuration = {
        "output_mode": output_mode,
    }

    if output_mode == "queue":
        # Configure queue output
        queue_type = os.getenv("QUEUE_TYPE", "memory").lower()

        if queue_type not in ["memory", "kafka"]:
            raise ValueError(
                f"QUEUE_TYPE must be 'memory' or 'kafka', but got {queue_type}"
            )

        output_configuration["queue_type"] = queue_type

    else:
        # Disk output configuration (default)
        output_configuration["base_storage_path"] = os.getenv("STORAGE_PATH", "dumps")

    kwargs["output_configuration"] = output_configuration

    return kwargs


if __name__ == "__main__":

    args = load_params()
    
    ScarpingTask(**args).start()
