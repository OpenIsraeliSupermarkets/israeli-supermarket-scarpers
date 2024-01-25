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
    HET_COHEN = all_scrappers.HetCohen
    KESHET = all_scrappers.Keshet
    KING_STORE = all_scrappers.KingStore
    MAAYAN_2000 = all_scrappers.Maayan2000
    MAHSANI_ASHUK = all_scrappers.MahsaniAShuk
    MEGA = all_scrappers.Mega
    NETIV_HASED = all_scrappers.NetivHased
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
    SUPER_SAPIR = all_scrappers.SuperSapir
    FRESH_MARKET_AND_SUPER_DOSH = all_scrappers.FreshMarketAndSuperDosh
    QUIK = all_scrappers.Quik
    TIV_TAAM = all_scrappers.TivTaam
    VICTORY = all_scrappers.Victory
    YELLOW = all_scrappers.Yellow
    YOHANANOF = all_scrappers.Yohananof
    ZOL_VEBEGADOL = all_scrappers.ZolVeBegadol

    @classmethod
    def all_listed_scrappers(cls):
        """get all the scarpers and filter disabled scrapers"""
        return list(cls)

    @classmethod
    def all_active(cls):
        """get all the scarpers and filter disabled scrapers"""
        return (member for member in cls if cls.is_scraper_enabled(member))

    @classmethod
    def sample(cls, n=1):
        """sample n from the scrappers"""
        return random.sample(cls.all_scrapers_name(), n)

    @classmethod
    def all_scrapers(cls):
        """list all scrapers possible to use"""
        return [e.value for e in ScraperFactory.all_active()]

    @classmethod
    def all_scrapers_name(cls):
        """get the class name of all listed scrapers"""
        return [e.name for e in ScraperFactory.all_active()]

    @classmethod
    def get(cls, class_name):
        """get a scraper by class name"""
        enum = None
        if isinstance(class_name, ScraperFactory):
            enum = class_name
        elif class_name in cls.all_scrapers_name():
            enum = getattr(ScraperFactory, class_name)
        else:
            raise ValueError(f"class_names {class_name} not found")
        if not cls.is_scraper_enabled(enum):
            return None
        return enum.value

    @classmethod
    def is_scraper_enabled(cls, enum):
        """get scraper value base on the enum value, if it disabled, return None"""
        env_var_value = os.environ.get("DISABLED_SCRAPPERS")
        if env_var_value is not None:
            disabled_scrappers = list(map(str.strip, env_var_value.split(",")))
            if enum.name in disabled_scrappers:
                return False
        return True
