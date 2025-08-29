from il_supermarket_scarper.engines import Matrix
from il_supermarket_scarper.utils import DumpFolderNames


class HetCohen(Matrix):
    """scraper for ChetCohen"""

    def __init__(self, streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.HET_COHEN,
            chain_id=["7290455000004"],
            chain_hebrew_name="ח. כהן",
            streaming_config=streaming_config
        )
