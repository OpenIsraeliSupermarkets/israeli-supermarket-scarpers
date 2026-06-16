from il_supermarket_scarper.engines import Matrix
from il_supermarket_scarper.utils import DumpFolderNames
from il_supermarket_scarper.scrappers.victory import _LaibcatalogApiScraper


class HetCohen(Matrix):
    """scraper for ChetCohen"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.HET_COHEN,
            chain_id=["7290455000004"],
            file_output=file_output,
            status_database=status_database,
            chain_hebrew_name="ח. כהן",
        )


class HetCohenNewSource(_LaibcatalogApiScraper):
    """scraper for Het Cohen using laibcatalog.co.il API (hcohen/index.html)"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.HET_COHEN_NEW_SOURCE,
            chain_id=["7290455000004"],
            file_output=file_output,
            status_database=status_database,
        )
        self.chain_hebrew_name = "ח. כהן"
