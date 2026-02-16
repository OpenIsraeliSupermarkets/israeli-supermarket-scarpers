from il_supermarket_scarper.engines import Matrix
from il_supermarket_scarper.utils import DumpFolderNames


class Victory(Matrix):
    """scraper for victory"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.VICTORY,
            chain_hebrew_name="ויקטורי",
            chain_id=["7290696200003", "7290058103393"],
            folder_name=folder_name,
        )


class VictoryNewSource(Victory):
    """scraper for victory new source"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.VICTORY,
            url="https://laibcatalog.co.il/victory/index.html",
            chain_hebrew_name="ויקטורי",
            chain_id=["7290696200003", "7290058103393"],
            folder_name=folder_name,
        )
