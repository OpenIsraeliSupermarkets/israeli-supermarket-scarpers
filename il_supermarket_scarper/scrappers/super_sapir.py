from il_supermarket_scarper.engines import Bina


class SuperSapir(Bina):
    """scaper for super sapir"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="SuperSapir",
            chain_id="7290058156016",
            url_perfix="supersapir",
            folder_name=folder_name,
        )
