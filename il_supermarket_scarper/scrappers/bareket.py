from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import _is_saturday_in_israel, _is_holiday_in_israel
from il_supermarket_scarper.utils import FlakyScraper, DumpFolderNames


@FlakyScraper
class Bareket(Bina):
    """scarper for bareket"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.BAREKET,
            chain_id="7290875100001",
            url_perfix="superbareket",
            folder_name=folder_name,
        )

    def _is_validate_scraper_found_no_files(
        self, limit=None, files_types=None, store_id=None, only_latest=False
    ):
        # no data on shabat if you test a single store file.
        return _is_saturday_in_israel() or _is_holiday_in_israel() and store_id
