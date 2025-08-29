from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import FileTypesFilters, DumpFolderNames


class Cofix(Cerberus):
    """scraper for confix"""

    def __init__(self, streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.COFIX,
            chain_id="7291056200008",
            ftp_username="SuperCofixApp",
            streaming_config=streaming_config
        )

    def is_valid_file_empty(self, file_name):
        """it is valid the file is empty"""

        return super().is_valid_file_empty(
            file_name
        ) or FileTypesFilters.is_file_from_type(
            file_name, FileTypesFilters.STORE_FILE.name
        )
