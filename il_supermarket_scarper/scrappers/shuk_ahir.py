from il_supermarket_scarper.engines import Bina


class ShukAhir(Bina):
    """scraper for shuk a hir"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="Shuk Ahir",
            chain_id="7290058148776",
            url_perfix="shuk-hayir",
            folder_name=folder_name,
        )
