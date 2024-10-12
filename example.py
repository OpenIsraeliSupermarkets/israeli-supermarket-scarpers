from il_supermarket_scarper import ScarpingTask
from il_supermarket_scarper.utils import _now

if __name__ == "__main__":
    scraper = ScarpingTask(
        dump_folder_name="dumps",
        lookup_in_db=False,
        multiprocessing=2,
        # size_estimation_mode=True,  # download files,log size, delete files
        when_date=_now(),
    )
    scraper.start()
