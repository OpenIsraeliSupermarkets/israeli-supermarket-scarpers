from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class Polizer(Cerberus):
    """scarper for polizer"""

    def __init__(self, streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.POLIZER,
            chain_id="7291059100008",
            ftp_username="politzer",
            streaming_config=streaming_config
        )
