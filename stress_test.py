import time
import json
import datetime
import pstats
import cProfile
import io
import asyncio

from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import DiskFileOutput, Logger
from il_supermarket_scarper.utils.databases import AbstractDataBase
from il_supermarket_scarper.utils.status import _now


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that properly formats datetime objects."""

    def default(self, o):
        if isinstance(o, datetime.datetime):
            # Format datetime as ISO string with timezone info
            return o.isoformat()
        if isinstance(o, datetime.date):
            # Format date as ISO string
            return o.isoformat()
        if isinstance(o, datetime.time):
            # Format time as ISO string
            return o.isoformat()
        # Fallback to string representation for other non-serializable types
        try:
            return super().default(o)
        except TypeError:
            return str(o)


class NoOpStatusDatabase(AbstractDataBase):
    """In-memory database for stress testing performance.
    Collects all status data in memory without file I/O, then dumps to results."""

    def __init__(self, database_name):
        super().__init__(database_name)
        self._data = {}  # Store collections: {collection_name: [documents...]}

    def insert_document(self, collection_name, document):
        """Store document in memory collection."""
        if collection_name not in self._data:
            self._data[collection_name] = []
        self._data[collection_name].append(document)
        self._update_last_modified()

    def insert_documents(self, collection_name, document):
        """Store multiple documents in memory collection."""
        if collection_name not in self._data:
            self._data[collection_name] = []
        if isinstance(document, list):
            self._data[collection_name].extend(document)
        else:
            self._data[collection_name].append(document)
        self._update_last_modified()

    def already_downloaded(self, collection_name, query):
        """Always return False - assume nothing is downloaded."""
        return False

    def _update_last_modified(self):
        """Update the last modified timestamp to current time."""
        if "_metadata" not in self._data:
            self._data["_metadata"] = {}
        self._data["_metadata"]["last_modified"] = _now()

    def get_last_modified(self):
        """Get the last modified timestamp when scraper last wrote to this database."""
        if "_metadata" in self._data and "last_modified" in self._data["_metadata"]:
            return self._data["_metadata"]["last_modified"]
        return None

    def get_all_data(self):
        """Get all collected status data as a dictionary matching JsonDataBase format."""
        return dict(sorted(self._data.items()))


def format_stats_as_json(profile, project_name):
    """get the stats from the profiler and format them as json"""
    stream = io.StringIO()
    ps = pstats.Stats(profile, stream=stream)
    ps.sort_stats(pstats.SortKey.CUMULATIVE)  # Sort by cumulative time
    ps.print_stats()

    # Convert the printed stats to a list of lines
    stats_output = stream.getvalue().splitlines()

    # Filter the lines to include only functions within the project
    project_stats = []
    for line in stats_output:
        if project_name in line:  # Filter for project-specific lines

            parts = line.split()
            if len(parts) >= 5:  # Basic sanity check for the parts
                function_data = {
                    "function": parts[-1],  # Function path
                    "ncalls": parts[0],  # Number of calls
                    "tottime": parts[1],
                    "tottime_per_call": parts[2],  # Time spent in function
                    "cumtime": parts[3],  # Cumulative time including subcalls
                    "cumtime_per_call": parts[4],  #
                }
                project_stats.append(function_data)

    return project_stats


async def main():
    """Main function to run stress tests on scrapers."""
    results = {}
    for scraper_name in [
        ScraperFactory.SUPER_PHARM.name
    ]:  # ScraperFactory.BAREKET.name,

        async def full_execution(scraper):
            """Optimized full execution of the scraper for stress testing"""
            files = []
            error = None
            status_database = None

            Logger.set_logging_level("WARNING")
            try:
                # Use NoOpStatusDatabase for stress testing to avoid I/O overhead
                # It collects all status data in memory and we'll dump it to results
                status_database = NoOpStatusDatabase(database_name=scraper)

                # OPTIMIZATION: Use RAM disk if available for faster I/O
                storage_path = f"temp/{scraper}"

                initer = ScraperFactory.get(scraper)(
                    file_output=DiskFileOutput(storage_path=storage_path),
                    status_database=status_database,
                )
                async for result in initer.scrape(limit=100):
                    files.append(result)
            except Exception as e:  # pylint: disable=broad-exception-caught
                error = str(e)

            # Extract collected status data
            status_data = status_database.get_all_data() if status_database else {}
            return files, error, status_data

        execution_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = time.time()
        pr = cProfile.Profile()
        pr.enable()

        files, error, status_data = await full_execution(scraper_name)

        pr.disable()

        end_time = time.time()
        results[scraper_name] = {
            "status": format_stats_as_json(pr, "israeli-supermarket-scarpers"),
            "execution_time": execution_time,
            "start_time": start_time,
            "end_time": end_time,
            "time": end_time - start_time,
            "files": len(files),
            "error": error,
            "status_data": status_data,  # Dump collected status database data
        }

        with open("stress_test_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, cls=DateTimeEncoder, indent=2)


if __name__ == "__main__":

    asyncio.run(main())
