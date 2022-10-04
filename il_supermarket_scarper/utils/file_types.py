from enum import Enum


class FileTypesFilters(Enum):
    """type of files avaliable to download"""

    PROMO_FILE = "promo"
    STORE_FILE = "store"
    PRICE_FILE = "price"

    @classmethod
    def all_types(cls):
        """Returns a list of all the enum keys."""
        return [e.name for e in FileTypesFilters]

    @classmethod
    def only_promo(cls):
        """only files with promotion date"""
        return [FileTypesFilters.PROMO_FILE.name]

    @classmethod
    def only_store(cls):
        """only files with stores date"""
        return [FileTypesFilters.STORE_FILE.name]

    @classmethod
    def only_price(cls):
        """only files with prices date"""
        return [FileTypesFilters.PRICE_FILE.name]

    @staticmethod
    def filter_file(file_name, key_name):
        """fillter function"""
        return key_name in file_name.lower() and "null" not in file_name.lower()

    @classmethod
    def filter(cls, file_type, iterable, by=None):
        """Returns the type of the file."""
        string_to_look_in = getattr(cls, file_type).value
        if not by:
            by = lambda x: x
        return list(
            filter(
                lambda filename: cls.filter_file(by(filename), string_to_look_in),
                iterable,
            )
        )
