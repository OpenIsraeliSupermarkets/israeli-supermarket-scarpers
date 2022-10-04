from il_supermarket_scarper.engines import Bina


class Maayan2000(Bina):
    """scaper for maayan 2000"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="Maayan2000",
            chain_id="7290058159628",
            url_perfix="maayan2000",
            folder_name=folder_name,
        )
