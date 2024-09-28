from il_supermarket_scarper.scrappers_factory import ScraperFactory
import time,json
import datetime

if __name__ == "__main__":

    result = {}
    for scraper in ScraperFactory.all_scrapers_name():

        def full_execution():
            initer = ScraperFactory.get(scraper)()
            return initer.scrape(limit=None)
        
        execution_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = time.time()
        files = full_execution()
        end_time = time.time()
        result[scraper] = {
            "execution_time":execution_time,
            "start_time":start_time,
            "end_time":end_time,
            "time": end_time - start_time,
            "files": len(files)
        }
        
        with open("stress_test_results.json", "w") as f:
            json.dump(result, f)
    


    
