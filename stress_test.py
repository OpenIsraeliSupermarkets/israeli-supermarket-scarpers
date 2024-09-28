import time
import json
import datetime
from il_supermarket_scarper.scrappers_factory import ScraperFactory


if __name__ == "__main__":

    result = {}
    for scraper_name in ScraperFactory.all_scrapers_name():

        def full_execution(scraper):
            """full execution of the scraper"""
            initer = ScraperFactory.get(scraper)()
            return initer.scrape()

        execution_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = time.time()
        files = full_execution(scraper_name)
        end_time = time.time()
        result[scraper_name] = {
            "execution_time": execution_time,
            "start_time": start_time,
            "end_time": end_time,
            "time": end_time - start_time,
            "files": len(files),
        }

        with open("stress_test_results.json", "w", encoding="utf-8") as f:
            json.dump(result, f)
