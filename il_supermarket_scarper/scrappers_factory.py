import random
import os
from enum import Enum
import il_supermarket_scarper.scrappers as all_scrappers
from il_supermarket_scarper.scraper_stability import ScraperStability


class ScraperFactory(Enum):
    """all scrapers avaliabe"""

    BAREKET = all_scrappers.Bareket  # עוף והודו ברקת - חנות המפעל בע"מ
    YAYNO_BITAN = all_scrappers.YaynotBitan  # יינות ביתן
    COFIX = all_scrappers.Cofix  # קופיקס בע"מ
    # CITY_MARKET_GIVATAYIM = all_scrappers.CityMarketGivatayim
    # CITY_MARKET_KIRYATONO = all_scrappers.CityMarketKirtatOno
    CITY_MARKET_KIRYATGAT = all_scrappers.CityMarketKiryatGat  # סיטי מרקט
    CITY_MARKET_SHOPS = all_scrappers.CityMarketShops  # סיטי מרקט
    DOR_ALON = all_scrappers.DorAlon  # דור אלון ניהול מתחמים קמעונאיים בע"מ
    GOOD_PHARM = all_scrappers.GoodPharm  # גוד פארם בע"מ
    HAZI_HINAM = all_scrappers.HaziHinam  # כל בו חצי חינם בע"מ
    HET_COHEN = all_scrappers.HetCohen  # ח. כהן סוכנות מזון ומשקאות בע"מ
    KESHET = all_scrappers.Keshet  # קשת טעמים בע"מ
    KING_STORE = all_scrappers.KingStore  # אלמשהדאוי קינג סטור בע"מ
    MAAYAN_2000 = all_scrappers.Maayan2000  # ג.מ מעיין אלפיים (07) בע"מ
    MAHSANI_ASHUK = all_scrappers.MahsaniAShuk  # כ.נ מחסני השוק בע"מ
    MEGA = all_scrappers.Mega  # קרפור \ מגה
    NETIV_HASED = all_scrappers.NetivHased  # נתיב החסד - סופר חסד בע"מ (כולל ברכל)
    MESHMAT_YOSEF_1 = (
        all_scrappers.MeshnatYosef1
    )  # קיי.טי. יבוא ושיווק בע"מ (משנת יוסף)
    MESHMAT_YOSEF_2 = (
        all_scrappers.MeshnatYosef2
    )  # קיי.טי. יבוא ושיווק בע"מ (משנת יוסף)
    OSHER_AD = all_scrappers.Osherad  # מרב-מזון כל בע"מ (אושר עד)
    POLIZER = all_scrappers.Polizer  # פוליצר חדרה (1982) בע"מ
    RAMI_LEVY = all_scrappers.RamiLevy  # רשת חנויות רמי לוי שיווק השקמה 2006 בע"מ
    SALACH_DABACH = all_scrappers.SalachDabach  # סאלח דבאח ובניו בע"מ
    SHEFA_BARCART_ASHEM = all_scrappers.ShefaBarcartAshem  # שפע ברכת השם בע"מ
    SHUFERSAL = all_scrappers.Shufersal  # שופרסל בע"מ (כולל רשת BE)
    SHUK_AHIR = all_scrappers.ShukAhir  # שוק העיר (ט.ע.מ.ס) בע"מ
    STOP_MARKET = all_scrappers.StopMarket  # סטופ מרקט בע"מ
    SUPER_PHARM = all_scrappers.SuperPharm  # סופר פארם (ישראל) בע"מ
    SUPER_YUDA = all_scrappers.SuperYuda  # סופר יודה
    SUPER_SAPIR = all_scrappers.SuperSapir  # סופר ספיר בע"מ
    FRESH_MARKET_AND_SUPER_DOSH = all_scrappers.FreshMarketAndSuperDosh  # פרשמרקט
    QUIK = all_scrappers.Quik  # קוויק
    TIV_TAAM = all_scrappers.TivTaam  # טיב טעם רשתות בע"מ
    VICTORY = all_scrappers.Victory  # ויקטורי רשת סופרמרקטים בע"מ
    YELLOW = all_scrappers.Yellow  # יילו
    YOHANANOF = all_scrappers.Yohananof  # מ. יוחננוף ובניו (1988) בע"מ
    ZOL_VEBEGADOL = all_scrappers.ZolVeBegadol  # זול ובגדול בע"מ
    WOLT = all_scrappers.Wolt  # וולט אופריישנס סרוויסס ישראל בע"מ

    @classmethod
    def all_listed_scrappers(cls):
        """get all the scarpers and filter disabled scrapers"""
        return list(member.name for member in cls)

    @classmethod
    def all_active(cls, limit=None, files_types=None, when_date=None):
        """get all the scarpers and filter disabled scrapers"""
        return (
            member
            for member in cls
            if cls.is_scraper_enabled(
                member,
                limit=limit,
                files_types=files_types,
                when_date=when_date,
            )
        )

    @classmethod
    def sample(cls, n=1):
        """sample n from the scrappers"""
        return random.sample(cls.all_scrapers_name(), n)

    @classmethod
    def all_scrapers(cls, limit=None, files_types=None, when_date=None):
        """list all scrapers possible to use"""
        return [
            e.value
            for e in ScraperFactory.all_active(
                limit=limit, files_types=files_types, when_date=when_date
            )
        ]

    @classmethod
    def all_scrapers_name(cls, limit=None, files_types=None, when_date=None):
        """get the class name of all listed scrapers"""
        return [
            e.name
            for e in ScraperFactory.all_active(
                limit=limit, files_types=files_types, when_date=when_date
            )
        ]

    @classmethod
    def get(cls, class_name, limit=None, files_types=None, when_date=None):
        """get a scraper by class name"""

        enum = None
        if isinstance(class_name, ScraperFactory):
            enum = class_name
        elif class_name in cls.all_scrapers_name():
            enum = getattr(ScraperFactory, class_name)

        if enum is None:
            raise ValueError(f"class_names {class_name} not found")

        if not cls.is_scraper_enabled(
            enum, limit=limit, files_types=files_types, when_date=when_date
        ):
            return None
        return enum.value

    @classmethod
    def is_scraper_enabled(cls, enum, limit=None, files_types=None, when_date=None):
        """get scraper value base on the enum value, if it disabled, return None"""
        env_var_value = os.environ.get("DISABLED_SCRAPPERS")
        if env_var_value is not None:
            disabled_scrappers = list(map(str.strip, env_var_value.split(",")))
            if enum.name in disabled_scrappers:
                return False
        #
        if ScraperStability.is_validate_scraper_found_no_files(
            enum.name,
            limit=limit,
            files_types=files_types,
            when_date=when_date,
            utilize_date_param=enum.value.utilize_date_param,
        ):
            return False
        return True
