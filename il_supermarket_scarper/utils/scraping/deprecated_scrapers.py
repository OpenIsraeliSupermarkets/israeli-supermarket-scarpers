from enum import Enum


class DeprecatedScrapers(Enum):
    """scrapers no longer on gov.il or replaced by a new source"""

    # Replaced by new sources (gov.il lists new source only):
    VICTORY = "Victory"  # replaced by VICTORY_NEW_SOURCE (laibcatalog API)
    HET_COHEN = "HetCohen"  # replaced by HET_COHEN_NEW_SOURCE (laibcatalog API)
    MAHSANI_ASHUK = "MahsaniAShuk"  # replaced by MAHSANI_ASHUK_NEW_SOURCE
    # Removed from gov.il / folded into other chains:
    COFIX = "Cofix"  # gov.il 12.08.2026 folded into Rami Levy
    MEGA = "Mega"  # merged with other chains
    CITY_MARKET_GIVATAYIM = "CityMarketGivatayim"  # closed
    CITY_MARKET_KIRYATONO = "CityMarketKiryatOno"  # closed
    # Site permanently down (DNS fails), no longer on gov.il dedicated listing:
    QUIK = "Quik"  # gov.il 12.08.2026 dropped dedicated link (under Rami Levy)

    @classmethod
    def names(cls):
        """get the names of all deprecated scrapers"""
        return {member.name for member in cls}
