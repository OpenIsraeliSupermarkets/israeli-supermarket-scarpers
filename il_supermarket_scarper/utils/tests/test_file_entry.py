"""Parse one listing date with the caller's format. Never scan keys or dump names."""

import unittest

from il_supermarket_scarper.engines.bina import Bina
from il_supermarket_scarper.engines.matrix import Matrix
from il_supermarket_scarper.engines.multipage_web import MultiPageWeb
from il_supermarket_scarper.engines.publishprice import PublishPrice
from il_supermarket_scarper.scrappers.city_market import CityMarketShops
from il_supermarket_scarper.scrappers.hazihinam import HaziHinam
from il_supermarket_scarper.scrappers.meshnat_yosef import MeshnatYosef1
from il_supermarket_scarper.scrappers.nativ_hashed import NetivHased
from il_supermarket_scarper.scrappers.shufersal import Shufersal
from il_supermarket_scarper.scrappers.super_pharm import SuperPharm
from il_supermarket_scarper.scrappers.victory import VictoryNewSource
from il_supermarket_scarper.utils import FileEntry
from il_supermarket_scarper.utils.connection import _ftp_mlsd_published_at


class TestParsePublishedAt(unittest.TestCase):
    """Each scraper supplies one format; samples from live UIs on 2026-09-09."""

    def test_bina_datefile(self):
        """Bina listing timestamps are ``HH:MM DD/MM/YYYY``."""
        self.assertEqual(
            FileEntry.parse_published_at(
                "14:18 08/09/2026", Bina.listing_date_format
            ),
            "2026-09-08T14:18:00",
        )

    def test_shufersal_update_time(self):
        """Shufersal uses MultiPageWeb's ``M/D/YYYY h:mm:ss AM/PM`` format."""
        self.assertEqual(Shufersal.listing_date_format, MultiPageWeb.listing_date_format)
        self.assertEqual(
            FileEntry.parse_published_at(
                "9/8/2026 2:00:00 AM", Shufersal.listing_date_format
            ),
            "2026-09-08T02:00:00",
        )

    def test_super_pharm_mdy(self):
        """Super Pharm listing timestamps are ``MM/DD/YYYY HH:MM:SS``."""
        self.assertEqual(
            FileEntry.parse_published_at(
                "09/08/2026 19:40:10", SuperPharm.listing_date_format
            ),
            "2026-09-08T19:40:10",
        )

    def test_hazi_hinam_and_city_market(self):
        """Hazi Hinam and City Market Shops share ``DD-MM-YYYY HH:MM``."""
        self.assertEqual(
            HaziHinam.listing_date_format, CityMarketShops.listing_date_format
        )
        self.assertEqual(
            FileEntry.parse_published_at(
                "09-09-2026 00:20", HaziHinam.listing_date_format
            ),
            "2026-09-09T00:20:00",
        )
        self.assertEqual(
            FileEntry.parse_published_at(
                "08-09-2026 23:50", CityMarketShops.listing_date_format
            ),
            "2026-09-08T23:50:00",
        )

    def test_publishprice_modified(self):
        """PublishPrice listing timestamps are ``HH:MM DD-MM-YYYY``."""
        self.assertEqual(
            FileEntry.parse_published_at(
                "00:01 09-09-2026", PublishPrice.listing_date_format
            ),
            "2026-09-09T00:01:00",
        )

    def test_meshnat_iso_date(self):
        """Meshmat Yosef listing timestamps are ``YYYY-MM-DD HH:MM:SS``."""
        self.assertEqual(
            FileEntry.parse_published_at(
                "2026-09-09 00:00:00", MeshnatYosef1.listing_date_format
            ),
            "2026-09-09T00:00:00",
        )

    def test_victory_file_date(self):
        """Victory API listing timestamps are ``YYYY-MM-DD HH:MM:SS``."""
        self.assertEqual(
            FileEntry.parse_published_at(
                "2026-09-11 22:30:37", VictoryNewSource.listing_date_format
            ),
            "2026-09-11T22:30:37",
        )

    def test_matrix_td_date(self):
        """Matrix listing timestamps are ``DD/MM/YYYY HH:MM:SS``."""
        self.assertEqual(
            FileEntry.parse_published_at(
                "11/09/2026 06:27:02", Matrix.listing_date_format
            ),
            "2026-09-11T06:27:02",
        )

    def test_netiv_file_date(self):
        """Netiv listing timestamps are ``DD/MM/YYYY HH:MM``."""
        self.assertEqual(
            FileEntry.parse_published_at(
                "11/09/2026 14:23", NetivHased.listing_date_format
            ),
            "2026-09-11T14:23:00",
        )

    def test_ftp_mlsd_modify(self):
        """FTP MLSD modify facts are ``YYYYMMDDHHMMSS``."""
        self.assertEqual(
            _ftp_mlsd_published_at({"modify": "20260911143037"}),
            "2026-09-11T14:30:37",
        )
        self.assertIsNone(_ftp_mlsd_published_at({}))

    def test_wrong_format_is_none(self):
        """A scraper must not try every format; mismatch stays None."""
        self.assertIsNone(
            FileEntry.parse_published_at(
                "14:18 08/09/2026", Shufersal.listing_date_format
            )
        )
        self.assertIsNone(FileEntry.parse_published_at(None, Bina.listing_date_format))
        self.assertIsNone(
            FileEntry.parse_published_at(
                "PromoFull7290058249350-000-043-20260909-000051.gz",
                Bina.listing_date_format,
            )
        )
