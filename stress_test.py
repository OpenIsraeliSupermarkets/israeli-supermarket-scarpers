import time
import json
import datetime
import tempfile
import pstats
import cProfile
import io
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import _now


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


if __name__ == "__main__":

    result = {}
    for scraper_name in ScraperFactory.all_scrapers_name():

        def full_execution(scraper):
            """full execution of the scraper"""
            with tempfile.TemporaryDirectory() as tmpdirname:
                try:
                    initer = ScraperFactory.get(scraper)(folder_name=tmpdirname)
                    return initer.scrape(when_date=_now()), ""
                except Exception as e:  # pylint: disable=broad-exception-caught
                    return [], str(e)

        execution_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = time.time()
        pr = cProfile.Profile()
        pr.enable()

        files, error = full_execution(scraper_name)

        pr.disable()

        end_time = time.time()
        result[scraper_name] = {
            "status": format_stats_as_json(pr, "israeli-supermarket-scarpers"),
            "execution_time": execution_time,
            "start_time": start_time,
            "end_time": end_time,
            "time": end_time - start_time,
            "files": len(files),
            "error": error,
        }

        with open("stress_test_results.json", "w", encoding="utf-8") as f:
            json.dump(result, f)
