"""One representative scraper per engine class, and the mocker that feeds it."""

from dataclasses import dataclass

from il_supermarket_scarper.engines import (
    ApiWebEngine,
    Bina,
    Cerberus,
    Matrix,
    MultiPageWeb,
    PublishPrice,
)
from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.scrappers_factory import ScraperFactory

from .mockers import (
    ApiMocker,
    BinaMocker,
    FtpMocker,
    MatrixMocker,
    MultiPageMocker,
    Mocker,
    PlainWebMocker,
    PublishPriceMocker,
)


@dataclass(frozen=True)
class EngineCase:
    """An engine class, the scraper used to exercise it and its mocker."""

    engine_cls: type
    scraper_name: str  # ScraperFactory member name
    mocker_cls: type[Mocker]

    @property
    def scraper_cls(self):
        """The scraper class looked up in ``ScraperFactory``."""
        return ScraperFactory[self.scraper_name].value


ENGINE_CASES = [
    EngineCase(Cerberus, "RAMI_LEVY", FtpMocker),
    EngineCase(Bina, "BAREKET", BinaMocker),
    EngineCase(Matrix, "HET_COHEN", MatrixMocker),
    EngineCase(PublishPrice, "YAYNO_BITAN_AND_CARREFOUR", PublishPriceMocker),
    EngineCase(MultiPageWeb, "SHUFERSAL", MultiPageMocker),
    EngineCase(ApiWebEngine, "HET_COHEN_NEW_SOURCE", ApiMocker),
    EngineCase(WebBase, "MESHMAT_YOSEF_1", PlainWebMocker),
]
