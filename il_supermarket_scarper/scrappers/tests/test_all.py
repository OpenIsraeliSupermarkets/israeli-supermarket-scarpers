# pylint: disable=missing-class-docstring,wildcard-import
import pytest

from il_supermarket_scarper.scrappers_factory import ScraperFactory
from .test_cases import make_test_case


@pytest.mark.run(order=1)
class BareketTestCase(make_test_case(ScraperFactory.BAREKET, 2)):
    pass


@pytest.mark.run(order=2)
class YaynotBitanTestCase(make_test_case(ScraperFactory.YAYNO_BITAN, 6)):
    pass


@pytest.mark.run(order=3)
class CofixTestCase(make_test_case(ScraperFactory.COFIX, 299)):
    pass


@pytest.mark.run(order=4)
class DorAlonTestCase(make_test_case(ScraperFactory.DOR_ALON, 501)):
    pass


@pytest.mark.run(order=5)
class GoodPharmTestCase(make_test_case(ScraperFactory.GOOD_PHARM, 952)):
    pass


@pytest.mark.run(order=6)
class HaziHinamTestCase(make_test_case(ScraperFactory.HAZI_HINAM, 2)):
    pass


@pytest.mark.run(order=7)
class KeshetTestCase(make_test_case(ScraperFactory.KESHET, 5)):
    pass


@pytest.mark.run(order=8)
class KingStoreTestCase(make_test_case(ScraperFactory.KING_STORE, 334)):
    pass


@pytest.mark.run(order=9)
class Maayan2000TestCase(make_test_case(ScraperFactory.MAAYAN_2000, 60)):
    pass


@pytest.mark.run(order=10)
class MahsaniAShukTestCase(make_test_case(ScraperFactory.MAHSANI_ASHUK, 98)):
    pass


@pytest.mark.run(order=11)
class MegaMarketTestCase(make_test_case(ScraperFactory.MEGA_MARKET, 2150)):
    pass


@pytest.mark.run(order=12)
class MegaTestCase(make_test_case(ScraperFactory.MEGA, 37)):
    pass


@pytest.mark.run(order=13)
class NetivHasefTestCase(make_test_case(ScraperFactory.NETIV_HASED, 1)):
    pass


@pytest.mark.run(order=14)
class OsheradTestCase(make_test_case(ScraperFactory.OSHER_AD, 1)):
    pass


@pytest.mark.run(order=15)
class PolizerTestCase(make_test_case(ScraperFactory.POLIZER, 1)):
    pass


@pytest.mark.run(order=16)
class RamiLevyTestCase(make_test_case(ScraperFactory.RAMI_LEVY, 1)):
    pass


@pytest.mark.run(order=17)
class SalachDabachTestCase(make_test_case(ScraperFactory.SALACH_DABACH, 4)):
    pass


@pytest.mark.run(order=18)
class ShefaBarcartAshemTestCase(make_test_case(ScraperFactory.SHEFA_BARCART_ASHEM, 41)):
    pass


@pytest.mark.run(order=19)
class ShufersalTestCase(make_test_case(ScraperFactory.SHUFERSAL, 176)):
    pass


@pytest.mark.run(order=20)
class ShukAhirTestCase(make_test_case(ScraperFactory.SHUK_AHIR, 4)):
    pass


@pytest.mark.run(order=21)
class StopMarketTestCase(make_test_case(ScraperFactory.STOP_MARKET, 5)):
    pass


@pytest.mark.run(order=22)
class SuperPharmTestCase(make_test_case(ScraperFactory.SUPER_PHARM, 224)):
    pass


@pytest.mark.run(order=23)
class SuperYudaTestCase(make_test_case(ScraperFactory.SUPER_YUDA, 40)):
    pass


@pytest.mark.run(order=24)
class FreshMarketAndSuperDoshTestCase(
    make_test_case(ScraperFactory.FRESH_MARKET_AND_SUPER_DOSH, 1)
):
    pass


@pytest.mark.run(order=25)
class TivTaamTestCase(make_test_case(ScraperFactory.TIV_TAAM, 2)):
    pass


@pytest.mark.run(order=26)
class VictoryTestCase(make_test_case(ScraperFactory.VICTORY, 1)):
    pass


@pytest.mark.run(order=27)
class YellowTestCase(make_test_case(ScraperFactory.YELLOW, 100)):
    pass


@pytest.mark.run(order=28)
class YohananofTestCase(make_test_case(ScraperFactory.YOHANANOF, 1)):
    pass


@pytest.mark.run(order=29)
class ZolVeBegadolTestCase(make_test_case(ScraperFactory.ZOL_VEBEGADOL, 4)):
    pass
