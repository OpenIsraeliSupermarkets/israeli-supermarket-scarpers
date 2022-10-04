from il_supermarket_scarper.engines import Cerberus


class HaziHinam(Cerberus):
    """scrper fro hazi hinam"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="Hazi Hinam",
            chain_id="7290700100008",
            folder_name=folder_name,
            ftp_username="HaziHinam",
        )
