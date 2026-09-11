"""Parse one listing date with the caller's format. Never scan keys or dump names."""

import unittest

from il_supermarket_scarper.engines.bina import Bina
from il_supermarket_scarper.engines.multipage_web import MultiPageWeb
from il_supermarket_scarper.engines.publishprice import PublishPrice
from il_supermarket_scarper.scrappers.city_market import CityMarketShops
from il_supermarket_scarper.scrappers.hazihinam import HaziHinam
from il_supermarket_scarper.scrappers.meshnat_yosef import MeshnatYosef1
from il_supermarket_scarper.scrappers.shufersal import Shufersal
from il_supermarket_scarper.scrappers.super_pharm import SuperPharm
from il_supermarket_scarper.utils import FileEntry


class TestParsePublishedAt(unittest.TestCase):
    """Each scraper supplies one format; samples from live UIs on 2026-09-09."""

    def test_bina_datefile(self):
        self.assertEqual(
            FileEntry.parse_published_at(
                "14:18 08/09/2026", Bina.listing_date_format
            ),
            "2026-09-08T14:18:00",
        )

    def test_shufersal_update_time(self):
        self.assertEqual(Shufersal.listing_date_format, MultiPageWeb.listing_date_format)
        self.assertEqual(
            FileEntry.parse_published_at(
                "9/8/2026 2:00:00 AM", Shufersal.listing_date_format
            ),
            "2026-09-08T02:00:00",
        )

    def test_super_pharm_mdy(self):
        self.assertEqual(
            FileEntry.parse_published_at(
                "09/08/2026 19:40:10", SuperPharm.listing_date_format
            ),
            "2026-09-08T19:40:10",
        )

    def test_hazi_hinam_and_city_market(self):
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
        self.assertEqual(
            FileEntry.parse_published_at(
                "00:01 09-09-2026", PublishPrice.listing_date_format
            ),
            "2026-09-09T00:01:00",
        )

    def test_meshnat_iso_date(self):
        self.assertEqual(
            FileEntry.parse_published_at(
                "2026-09-09 00:00:00", MeshnatYosef1.listing_date_format
            ),
            "2026-09-09T00:00:00",
        )

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
