from il_supermarket_scarper import MainScrapperRunner

if __name__ == '__main__':

    scraper = MainScrapperRunner(dump_folder_name="dumps",lookup_in_db=True)
    scraper.run()