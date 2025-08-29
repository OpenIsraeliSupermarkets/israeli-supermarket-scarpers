from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class Bareket(Bina):
    """scarper for bareket"""

    def __init__(self, streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.BAREKET,
            chain_id="7290875100001",
            url_perfix="superbareket",
            streaming_config=streaming_config
        )
