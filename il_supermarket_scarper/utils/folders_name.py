from enum import Enum


class DumpFolderNames(Enum):
    """all the folder that files will be download to"""

    BAREKET = "Bareket"
    YAYNO_BITAN = "YaynotBitan"
    COFIX = "Cofix"
    CITY_MARKET_GIVATAYIM = "CityMarketGivatayim"
    CITY_MARKET_KIRYATONO = "CityMarketKiryatOno"
    CITY_MARKET_KIRYATGAT = "CityMarketKiryatGat"
    CITY_MARKET_SHOPS = "CityMarketShops"
    DOR_ALON = "DorAlon"
    GOOD_PHARM = "GoodPharm"
    HAZI_HINAM = "HaziHinam"
    HET_COHEN = "HetCohen"
    KESHET = "Keshet"
    KING_STORE = "KingStore"
    MAAYAN_2000 = "Maayan2000"
    MAHSANI_ASHUK = "MahsaniAShuk"
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
    QUIK = "Quik"
    TIV_TAAM = "TivTaam"
    VICTORY = "Victory"
    YELLOW = "Yellow"
    YOHANANOF = "Yohananof"
    ZOL_VEBEGADOL = "ZolVeBegadol"

    @classmethod
    def is_valid_folder_name(cls, member):
        """check if an folder is part of the cls"""
        return isinstance(member, DumpFolderNames)

    @classmethod
    def all_folders_names(cls):
        """get the name of all listed folders"""
        return [e.name for e in cls]
