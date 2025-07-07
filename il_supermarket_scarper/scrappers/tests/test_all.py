from il_supermarket_scarper.scrappers_factory import ScraperFactory
from .test_cases import make_test_case


class BareketTestCase(make_test_case(ScraperFactory.BAREKET, 5)):
    """Test case for ScraperFactory.BAREKET."""


class YaynotBitanAndCarrefourTestCase(
    make_test_case(ScraperFactory.YAYNO_BITAN_AND_CARREFOUR, 9032)
):
    """Test case for ScraperFactory.YAYNO_BITAN_AND_CARREFOUR."""


class CofixTestCase(make_test_case(ScraperFactory.COFIX, 299)):
    """Test case for ScraperFactory.COFIX."""


# class CityMarketGivatayimTestCase(
#     make_test_case(ScraperFactory.CITY_MARKET_GIVATAYIM, 1)
# ):
#     """Test case for CityMarketGivatay"""


# class CityMarketKirtatOnoTestCase(
#     make_test_case(ScraperFactory.CITY_MARKET_KIRYATONO, 1)
# ):
#     """Test case for CityMarketKirtatOno"""


class CityMarketKiryatGatTestCase(
    make_test_case(ScraperFactory.CITY_MARKET_KIRYATGAT, 1)
):
    """Test case for CityMarketKiryatGat"""


class CityMarketShopsTestCase(make_test_case(ScraperFactory.CITY_MARKET_SHOPS, 1)):
    """Test case for CityMarketShops"""


class DorAlonTestCase(make_test_case(ScraperFactory.DOR_ALON, 501)):
    """Test case for ScraperFactory.DOR_ALON."""


class GoodPharmTestCase(make_test_case(ScraperFactory.GOOD_PHARM, 952)):
    """Test case for ScraperFactory.GOOD_PHARM."""


class HaziHinamTestCase(make_test_case(ScraperFactory.HAZI_HINAM, 206)):
    """Test case for ScraperFactory.HAZI_HINAM."""


class HetCohen(make_test_case(ScraperFactory.HET_COHEN, 45)):
    """Test case for ScraperFactory.HET_COHEN."""


class KeshetTestCase(make_test_case(ScraperFactory.KESHET, 5)):
    """Test case for ScraperFactory.KESHET."""


class KingStoreTestCase(make_test_case(ScraperFactory.KING_STORE, 334)):
    """Test case for ScraperFactory.KING_STORE."""


class Maayan2000TestCase(make_test_case(ScraperFactory.MAAYAN_2000, 60)):
    """Test case for ScraperFactory.MAAYAN_2000."""


class MahsaniAShukTestCase(make_test_case(ScraperFactory.MAHSANI_ASHUK, 98)):
    """Test case for ScraperFactory.MAHSANI_ASHUK."""


# class MegaTestCase(make_test_case(ScraperFactory.MEGA, 37)):
#     """Test case for ScraperFactory.MEGA."""


class NetivHasefTestCase(make_test_case(ScraperFactory.NETIV_HASED, 1)):
    """Test case for ScraperFactory.NETIV_HASED."""


class MeshnatYosef1TestCase(make_test_case(ScraperFactory.MESHMAT_YOSEF_1, 1)):
    """Test case for ScraperFactory.MESHMAT_YOSEF_1."""


class MeshnatYosef2TestCase(make_test_case(ScraperFactory.MESHMAT_YOSEF_2, 1)):
    """Test case for ScraperFactory.MESHMAT_YOSEF_2."""


class OsheradTestCase(make_test_case(ScraperFactory.OSHER_AD, 1)):
    """Test case for ScraperFactory.OSHER_AD."""


class PolizerTestCase(make_test_case(ScraperFactory.POLIZER, 1)):
    """Test case for ScraperFactory.POLIZER."""


class RamiLevyTestCase(make_test_case(ScraperFactory.RAMI_LEVY, 1)):
    """Test case for ScraperFactory.RAMI_LEVY."""


class SalachDabachTestCase(make_test_case(ScraperFactory.SALACH_DABACH, 4)):
    """Test case for ScraperFactory.SALACH_DABACH."""


class ShefaBarcartAshemTestCase(make_test_case(ScraperFactory.SHEFA_BARCART_ASHEM, 41)):
    """Test case for ScraperFactory.SHEFA_BARCART_ASHEM."""


class ShufersalTestCase(make_test_case(ScraperFactory.SHUFERSAL, 176)):
    """Test case for ScraperFactory.SHUFERSAL."""


class ShukAhirTestCase(make_test_case(ScraperFactory.SHUK_AHIR, 4)):
    """Test case for ScraperFactory.SHUK_AHIR."""


class StopMarketTestCase(make_test_case(ScraperFactory.STOP_MARKET, 5)):
    """Test case for ScraperFactory.STOP_MARKET."""


class SuperPharmTestCase(make_test_case(ScraperFactory.SUPER_PHARM, 224)):
    """Test case for ScraperFactory.SUPER_PHARM."""


class SuperYudaTestCase(make_test_case(ScraperFactory.SUPER_YUDA, 204)):
    """Test case for ScraperFactory.SUPER_YUDA."""


class SuperSapirTestCase(make_test_case(ScraperFactory.SUPER_SAPIR, 44)):
    """Test case for ScraperFactory.SUPER_SAPIR."""


class FreshMarketAndSuperDoshTestCase(
    make_test_case(ScraperFactory.FRESH_MARKET_AND_SUPER_DOSH, 1)
):
    """Test case for ScraperFactory.FRESH_MARKET_AND_SUPER_DOSH."""


class QuikTestCase(make_test_case(ScraperFactory.QUIK, None)):
    """Test case for ScraperFactory.QUIK."""


class TivTaamTestCase(make_test_case(ScraperFactory.TIV_TAAM, 3)):
    """Test case for ScraperFactory.TIV_TAAM."""


class VictoryTestCase(make_test_case(ScraperFactory.VICTORY, 1)):
    """Test case for ScraperFactory.VICTORY."""


class YellowTestCase(make_test_case(ScraperFactory.YELLOW, 1272)):
    """Test case for ScraperFactory.YELLOW."""


class YohananofTestCase(make_test_case(ScraperFactory.YOHANANOF, 1)):
    """Test case for ScraperFactory.YOHANANOF."""


class ZolVeBegadolTestCase(make_test_case(ScraperFactory.ZOL_VEBEGADOL, 4)):
    """Test case for ScraperFactory.ZOL_VEBEGADOL."""


class WoltTestCase(make_test_case(ScraperFactory.WOLT, 0)):
    """Test case for ScraperFactory.Wolt."""
