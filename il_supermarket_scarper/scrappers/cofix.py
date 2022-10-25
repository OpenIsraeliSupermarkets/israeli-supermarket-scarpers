from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import FileTypesFilters


class Cofix(Cerberus):
    """scraper for confix"""

    def __init__(self, folder_name=None):
        super().__init__(
            "cofix",
            chain_id="7291056200008",
            folder_name=folder_name,
            ftp_username="SuperCofixApp",
        )

    def is_valid_file_empty(self, file_name):
        """it is valid the file is empty"""

        return super().is_valid_file_empty(
            file_name
        ) or FileTypesFilters.is_file_from_type(
            file_name, FileTypesFilters.STORE_FILE.name
        )
