import time
import json
import datetime
import tempfile
import pstats
import cProfile
import io
import asyncio
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import DiskFileOutput, JsonDataBase


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
    results = {}
    for scraper_name in [ScraperFactory.BAREKET.name]:

        async def full_execution(scraper):
            """full execution of the scraper"""
            files = []
            error = None
            try:
                initer = ScraperFactory.get(scraper)(
                    file_output=DiskFileOutput(storage_path=f"temp/{scraper}"),
                    status_database=JsonDataBase(
                        database_name=scraper, base_path=f"temp/{scraper}"
                    ),
                )
                async for result in initer.scrape(limit=100):
                    files.append(result)
            except Exception as e:  # pylint: disable=broad-exception-caught
                error = str(e)
            return files, error

        execution_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = time.time()
        pr = cProfile.Profile()
        pr.enable()

        files, error = await full_execution(scraper_name)

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
        }

        with open("stress_test_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f)


if __name__ == "__main__":

    asyncio.run(main())
