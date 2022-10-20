from enum import Enum


class FileTypesFilters(Enum):
    """type of files avaliable to download"""

    PROMO_FILE = {
        "should_contain": "promo",
        "should_not_contain": "full",
    }
    STORE_FILE = {
        "should_contain": "store",
        "should_not_contain": None,
    }
    PRICE_FILE = {
        "should_contain": "price",
        "should_not_contain": "full",
    }
    PROMO_FULL_FILE = {
        "should_contain": "promofull",
        "should_not_contain": None,
    }
    PRICE_FULL_FILE = {
        "should_contain": "pricefull",
        "should_not_contain": None,
    }

    @classmethod
    def all_types(cls):
        """Returns a list of all the enum keys."""
        return [e.name for e in FileTypesFilters]

    @classmethod
    def only_promo(cls):
        """only files with promotion date"""
        return [FileTypesFilters.PROMO_FILE.name, FileTypesFilters.PROMO_FULL_FILE.name]

    @classmethod
    def only_store(cls):
        """only files with stores date"""
        return [FileTypesFilters.STORE_FILE.name]

    @classmethod
    def only_price(cls):
        """only files with prices date"""
        return [FileTypesFilters.PRICE_FILE.name, FileTypesFilters.PRICE_FULL_FILE.name]

    @staticmethod
    def filter_file(file_name, should_contain, should_not_contain):
        """fillter function"""
        return (
            should_contain in file_name.lower()
            and "null" not in file_name.lower()
            and (
                should_not_contain is None
                or should_not_contain not in file_name.lower()
            )
        )

    @classmethod
    def filter(cls, file_type, iterable, by_function=lambda x: x):
        """Returns the type of the file."""
        string_to_look_in = getattr(cls, file_type).value
        return list(
            filter(
                lambda filename: cls.filter_file(
                    by_function(filename), **string_to_look_in
                ),
                iterable,
            )
        )
