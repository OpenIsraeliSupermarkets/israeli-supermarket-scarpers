import time
import json
import sys
import datetime
import tempfile
from il_supermarket_scarper.scrappers_factory import ScraperFactory
import pstats
import cProfile
from io import StringIO





if __name__ == "__main__":

    result = {}
    for scraper_name in ScraperFactory.all_scrapers_name():

        def full_execution(scraper):
            """full execution of the scraper"""
            with tempfile.TemporaryDirectory() as tmpdirname:
                initer = ScraperFactory.get(scraper)(folder_name=tmpdirname)
                return initer.scrape()

        execution_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = time.time()
        pr = cProfile.Profile()
        pr.enable()

        files = full_execution(scraper_name)

        pr.disable()

        stream = StringIO()
        ps = pstats.Stats(pr, stream=stream)
        ps.print_stats()
        stream.seek(0)

        end_time = time.time()
        result[scraper_name] = {
            "status": stream.read(),
            "execution_time": execution_time,
            "start_time": start_time,
            "end_time": end_time,
            "time": end_time - start_time,
            "files": len(files),
        }

        with open("stress_test_results.json", "w", encoding="utf-8") as f:
            json.dump(result, f)
