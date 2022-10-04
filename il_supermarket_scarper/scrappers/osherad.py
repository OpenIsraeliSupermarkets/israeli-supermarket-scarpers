from il_supermarket_scarper.engines import Cerberus


class Osherad(Cerberus):
    """scaper for osher ad"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="Osher Ad",
            chain_id="7290103152017",
            folder_name=folder_name,
            ftp_username="osherad",
        )
