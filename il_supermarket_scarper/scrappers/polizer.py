from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class Polizer(Cerberus):
    """scarper for polizer"""

    def __init__(self, file_output=None):
        super().__init__(
            chain=DumpFolderNames.POLIZER,
            chain_id="7291059100008",
            file_output=file_output,
            ftp_username="politzer",
        )
