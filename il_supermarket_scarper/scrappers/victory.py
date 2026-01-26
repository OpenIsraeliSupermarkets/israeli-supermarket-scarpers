from il_supermarket_scarper.engines import Matrix
from il_supermarket_scarper.utils import DumpFolderNames


class Victory(Matrix):
    """scraper for victory"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.VICTORY,
            chain_hebrew_name="ויקטורי",
            chain_id=["7290696200003", "7290058103393"],
            file_output=file_output,
            status_database=status_database,
        )
