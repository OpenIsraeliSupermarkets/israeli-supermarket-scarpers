from il_supermarket_scarper.engines import Bina


class GoodPharm(Bina):
    """scarper from good pharm"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="GoodPharm",
            chain_id="7290058197699",
            url_perfix="goodpharm",
            folder_name=folder_name,
        )
