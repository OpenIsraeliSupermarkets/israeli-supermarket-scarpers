from enum import Enum


class DumpFolderNames(Enum):
    """all the folder that files will be download to"""

    BAREKET = "Bareket"
    # YAYNO_BITAN = "YaynotBitan"
    YAYNO_BITAN_AND_CARREFOUR = "YaynotBitanAndCarrefour"
    COFIX = "Cofix"  # deprecated: folded into Rami Levy (gov.il, 12.08.2026)
    CITY_MARKET_GIVATAYIM = "CityMarketGivatayim"
    CITY_MARKET_KIRYATONO = "CityMarketKiryatOno"
    CITY_MARKET_KIRYATGAT = "CityMarketKiryatGat"
    CITY_MARKET_SHOPS = "CityMarketShops"
    DOR_ALON = "DorAlon"
    GOOD_PHARM = "GoodPharm"
    HAZI_HINAM = "HaziHinam"
    HET_COHEN = "HetCohen"  # deprecated: use HET_COHEN_NEW_SOURCE
    HET_COHEN_NEW_SOURCE = "HetCohenNewSource"
    KESHET = "Keshet"
    KING_STORE = "KingStore"
    MAAYAN_2000 = "Maayan2000"
    MAHSANI_ASHUK = "MahsaniAShuk"  # deprecated: use MAHSANI_ASHUK_NEW_SOURCE
    MAHSANI_ASHUK_NEW_SOURCE = "MahsaniAShukNewSource"
    MEGA = "Mega"
    NETIV_HASED = "NetivHased"
    MESHMAT_YOSEF_1 = "MeshnatYosef1"
    MESHMAT_YOSEF_2 = "MeshnatYosef2"
    OSHER_AD = "Osherad"
    POLIZER = "Polizer"
    RAMI_LEVY = "RamiLevy"
    SALACH_DABACH = "SalachDabach"
    SHEFA_BARCART_ASHEM = "ShefaBarcartAshem"
    SHUFERSAL = "Shufersal"
    SHUK_AHIR = "ShukAhir"
    STOP_MARKET = "StopMarket"
    SUPER_PHARM = "SuperPharm"
    SUPER_YUDA = "SuperYuda"
    SUPER_SAPIR = "SuperSapir"
    FRESH_MARKET_AND_SUPER_DOSH = "FreshMarketAndSuperDosh"
    QUIK = "Quik"  # deprecated: folded into Rami Levy (gov.il, 12.08.2026)
    TIV_TAAM = "TivTaam"
    VICTORY = "Victory"  # deprecated: use VICTORY_NEW_SOURCE
    VICTORY_NEW_SOURCE = "VictoryNewSource"
    YELLOW = "Yellow"
    YOHANANOF = "Yohananof"
    ZOL_VEBEGADOL = "ZolVeBegadol"
    WOLT = "Wolt"

    @classmethod
    def is_valid_folder_name(cls, member):
        """check if an folder is part of the cls"""
        return isinstance(member, DumpFolderNames)

    @classmethod
    def all_folders_names(cls):
        """get the name of all listed folders (including deprecated ones)"""
        return [e.name for e in cls]

    @classmethod
    def active_folder_names(cls):
        """get the name of folders whose scraper is still active in ScraperFactory"""
        deprecated = {"COFIX", "QUIK", "HET_COHEN", "MAHSANI_ASHUK", "VICTORY"}
        return [e.name for e in cls if e.name not in deprecated]
