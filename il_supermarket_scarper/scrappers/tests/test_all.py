from il_supermarket_scarper.scrappers import *
from  .test_cases import make_test_case
from il_supermarket_scarper.utils import _is_saturday_in_israel
import pytest

@pytest.mark.run(order=1)
class DorAlonTestCase(make_test_case(DorAlon)):
    pass

@pytest.mark.run(order=2)
class HaziHinamTestCase(make_test_case(HaziHinam)):
    pass


@pytest.mark.run(order=3)
class KeshetTestCase(make_test_case(Keshet)):
    pass
@pytest.mark.run(order=4)
class OsheradTestCase(make_test_case(Osherad)):
    pass

@pytest.mark.run(order=5)
class RamiLevyTestCase(make_test_case(RamiLevy)):
    pass

@pytest.mark.run(order=6)
class CofixTestCase(make_test_case(Cofix)):
    pass
@pytest.mark.run(order=7)
class ShufersalTestCase(make_test_case(Shufersal)):
    pass

@pytest.mark.run(order=8)
class StopMarketTestCase(make_test_case(StopMarket)):
    pass

@pytest.mark.run(order=9)
class FreshMarketAndSuperDoshTestCase(make_test_case(FreshMarketAndSuperDosh)):
    pass

@pytest.mark.run(order=10)
class TivTaamTestCase(make_test_case(TivTaam)):
    pass

@pytest.mark.run(order=11)
class YohananofTestCase(make_test_case(Yohananof)):
    pass

@pytest.mark.run(order=11)
class SalachDabachTestCase(make_test_case(SalachDabach)):
    pass

@pytest.mark.run(order=12)
class PolizerTestCase(make_test_case(Polizer)):
    pass

@pytest.mark.run(order=13)
class YellowTestCase(make_test_case(Yellow)):
    pass
@pytest.mark.run(order=14)
class VictoryTestCase(make_test_case(Victory)):
    pass


@pytest.mark.run(order=15)
class MahsaniAShukTestCase(make_test_case(MahsaniAShuk)):
    pass

@pytest.mark.run(order=16)
class BareketTestCase(make_test_case(Bareket)):
    pass


@pytest.mark.run(order=17)
class ShukAhirTestCase(make_test_case(ShukAhir)):
    pass


@pytest.mark.run(order=18)
class ShefaBarcartAshemTestCase(make_test_case(ShefaBarcartAshem)):
    pass


@pytest.mark.run(order=19)
class SuperYudaTestCase(make_test_case(SuperYuda)):
    pass

@pytest.mark.run(order=20)
class ZolVeBegadolTestCase(make_test_case(ZolVeBegadol)):
    pass

@pytest.mark.run(order=21)
class Maayan2000TestCase(make_test_case(Maayan2000)):
    pass

@pytest.mark.run(order=22)
class KingStoreTestCase(make_test_case(KingStore)):
    pass

@pytest.mark.run(order=23)
class SuperPharmTestCase(make_test_case(SuperPharm)):
    pass

@pytest.mark.run(order=24)
class MegaTestCase(make_test_case(Mega)):
    pass

@pytest.mark.run(order=25)
class MegaMarketTestCase(make_test_case(MegaMarket)):
    pass

@pytest.mark.run(order=26)
class MegaMarketTestCase(make_test_case(MegaMarket)):
    pass

@pytest.mark.run(order=27)
class MegaMarketTestCase(make_test_case(MegaMarket)):
    pass

@pytest.mark.run(order=28)
class NetivHasefTestCase(make_test_case(NetivHasef)):
    pass
    # if not _is_saturday_in_israel():

@pytest.mark.run(order=29)
class GoodPharmTestCase(make_test_case(GoodPharm)):
    pass


    

