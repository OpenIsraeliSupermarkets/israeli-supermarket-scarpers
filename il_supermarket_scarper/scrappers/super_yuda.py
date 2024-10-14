from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class SuperYuda(Cerberus):
    """scraper for super yuda"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.SUPER_YUDA,
            chain_id=["7290058198450", "7290058177776"],
            ftp_username="yuda_ho",
            ftp_password="Yud@147",
            ftp_path="/Yuda",
            folder_name=folder_name,
        )
