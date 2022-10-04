from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import FileTypesFilters


class Polizer(Cerberus):
    """scarper for polizer"""

    def __init__(self, folder_name=None):
        super().__init__(
            "Polizer",
            chain_id="7291059100008",
            folder_name=folder_name,
            ftp_username="politzer",
        )

    def is_validate_scraper_found_no_files(self, limit=None, files_types=None):
        # no data on shabat
        result = super().is_validate_scraper_found_no_files(
            limit=limit, files_types=files_types
        )

        return result or (
            files_types is not None
            and len(files_types) == 1
            and files_types[0] == FileTypesFilters.STORE_FILE.name
        )
