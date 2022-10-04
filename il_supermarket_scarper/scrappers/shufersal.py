from il_supermarket_scarper.engines import MultiPageWeb


class Shufersal(MultiPageWeb):
    """scaper for shufersal"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="Shufersal", chain_id="7290027600007", folder_name=folder_name
        )
