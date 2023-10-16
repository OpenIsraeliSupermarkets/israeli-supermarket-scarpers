import random
import os
from enum import Enum
import il_supermarket_scarper.scrappers as all_scrappers


class ScraperFactory(Enum):
    """all scrapers avaliabe"""

    BAREKET = all_scrappers.Bareket
    YAYNO_BITAN = all_scrappers.YaynotBitan
    COFIX = all_scrappers.Cofix
    DOR_ALON = all_scrappers.DorAlon
    GOOD_PHARM = all_scrappers.GoodPharm
    HAZI_HINAM = all_scrappers.HaziHinam
    KESHET = all_scrappers.Keshet
    KING_STORE = all_scrappers.KingStore
    MAAYAN_2000 = all_scrappers.Maayan2000
    MAHSANI_ASHUK = all_scrappers.MahsaniAShuk
    MEGA_MARKET = all_scrappers.MegaMarket
    MEGA = all_scrappers.Mega
    NETIV_HASED = all_scrappers.NetivHasef
    OSHER_AD = all_scrappers.Osherad
    POLIZER = all_scrappers.Polizer
    RAMI_LEVY = all_scrappers.RamiLevy
    SALACH_DABACH = all_scrappers.SalachDabach
    SHEFA_BARCART_ASHEM = all_scrappers.ShefaBarcartAshem
    SHUFERSAL = all_scrappers.Shufersal
    SHUK_AHIR = all_scrappers.ShukAhir
    STOP_MARKET = all_scrappers.StopMarket
    SUPER_PHARM = all_scrappers.SuperPharm
    SUPER_YUDA = all_scrappers.SuperYuda
    FRESH_MARKET_AND_SUPER_DOSH = all_scrappers.FreshMarketAndSuperDosh
    TIV_TAAM = all_scrappers.TivTaam
    VICTORY = all_scrappers.Victory
    YELLOW = all_scrappers.Yellow
    YOHANANOF = all_scrappers.Yohananof
    ZOL_VEBEGADOL = all_scrappers.ZolVeBegadol

    @classmethod
    def get_scraper_init(cls, enum):
        """ get scraper value base on the enum value, if it disabled, return None """
        env_var_value = os.environ.get("DISABLED_SCRAPPERS")
        if env_var_value is not None:
            disabled_scrappers = list(map(str.strip, env_var_value.split(",")))
            if enum.name in disabled_scrappers:
                return None
        return enum.value

    @classmethod
    def __iter__(cls):
        """ get all the scarpers and filter disabled scrapers """
        return iter(member for member in cls if cls.get_scraper_init(member))

    @classmethod
    def sample(cls, n=1):
        """sample n from the scrappers"""
        return random.sample(cls.all_scrapers(), n)

    @classmethod
    def all_scrapers(cls):
        """list all scrapers possible to use"""
        return [e.value for e in ScraperFactory]

    @classmethod
    def all_scrapers_name(cls):
        """get the class name of all listed scrapers"""
        return [e.name for e in ScraperFactory]

    @classmethod
    def get(cls, class_name):
        """get a scraper by class name"""
        if isinstance(class_name, ScraperFactory):
            return class_name.value
        if class_name in cls.all_scrapers_name():
            return ScraperFactory[class_name].value
        raise ValueError(f"class_names {class_name} not found")
