from il_supermarket_scarper.engines import Matrix
from il_supermarket_scarper.utils import DumpFolderNames


class HetCohen(Matrix):
    """scraper for ChetCohen"""

    def __init__(self, file_output=None):
        super().__init__(
            chain=DumpFolderNames.HET_COHEN,
            chain_id=["7290455000004"],
            file_output=file_output,
            chain_hebrew_name="ח. כהן",
        )
