from il_supermarket_scarper.engines import Matrix
from il_supermarket_scarper.utils import DumpFolderNames


class HetCohen(Matrix):
    """scraper for ChetCohen"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.HET_COHEN,
            chain_id=["7290455000004"],
            folder_name=folder_name,
            chain_hebrew_name="ח. כהן",
        )
