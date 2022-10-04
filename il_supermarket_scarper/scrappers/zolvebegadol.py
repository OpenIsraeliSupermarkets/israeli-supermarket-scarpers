from il_supermarket_scarper.engines import Bina


class ZolVeBegadol(Bina):
    """scraper dfor zol-ve-begodol"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="ZolVeBegadol",
            chain_id="7290058173198",
            url_perfix="zolvebegadol",
            folder_name=folder_name,
        )
