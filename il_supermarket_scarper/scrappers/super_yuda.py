from il_supermarket_scarper.engines import Bina


class SuperYuda(Bina):
    """scraper for super yuda"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="SuperYuda",
            chain_id=["7290058198450", "7290058177776"],
            url_perfix="Paz",
            folder_name=folder_name,
        )
