from il_supermarket_scarper.engines import Matrix


class Bareket(Matrix):
    """scarper for bareket"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="bareket",
            chain_hebrew_name="סופר ברקת",
            chain_id="7290875100001",
            folder_name=folder_name,
        )
