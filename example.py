from il_supermarket_scarper import ScarpingTask

if __name__ == "__main__":

    scraper = ScarpingTask(
        dump_folder_name="dumps",
        lookup_in_db=False,
        multiprocessing=2,
        size_estimation_mode=True,  # download files,log size, delete files
    )
    scraper.start()
