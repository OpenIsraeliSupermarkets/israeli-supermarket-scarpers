from il_supermarket_scarper.engines import Matrix


class HetCohen(Matrix):
    """scraper for ChetCohen"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="ChetCohen",
            chain_hebrew_name="ח. כהן",
            chain_id=["7290455000004"],
            folder_name=folder_name,
        )
