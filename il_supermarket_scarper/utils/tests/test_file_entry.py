"""Parse one listing date with the caller's format. Never scan keys or dump names."""

import tempfile
import unittest

from il_supermarket_scarper.scrappers.bareket import Bareket
from il_supermarket_scarper.scrappers.city_market import CityMarketShops
from il_supermarket_scarper.scrappers.hazihinam import HaziHinam
from il_supermarket_scarper.scrappers.mega import Mega
from il_supermarket_scarper.scrappers.meshnat_yosef import MeshnatYosef1
from il_supermarket_scarper.scrappers.nativ_hashed import NetivHased
from il_supermarket_scarper.scrappers.shufersal import Shufersal
from il_supermarket_scarper.scrappers.super_pharm import SuperPharm
from il_supermarket_scarper.scrappers.victory import Victory, VictoryNewSource
from il_supermarket_scarper.utils import DiskFileOutput, FileEntry
from il_supermarket_scarper.utils.network.connection import _ftp_mlsd_published_at


class TestFileEntryId(unittest.TestCase):
    """Each FileEntry gets a stable unique id for one download story."""

    def test_entry_id_auto_generated_and_unique(self):
        a = FileEntry(name="a.xml", url="http://x/a", size=1)
        b = FileEntry(name="a.xml", url="http://x/a", size=1)
        self.assertTrue(a.entry_id)
        self.assertTrue(b.entry_id)
        self.assertNotEqual(a.entry_id, b.entry_id)

    def test_entry_id_can_be_supplied(self):
        entry = FileEntry(
            name="a.xml", url="http://x/a", size=1, entry_id="story-1"
        )
        self.assertEqual(entry.entry_id, "story-1")

    def test_listing_hash_ignores_entry_id(self):
        a = FileEntry(name="a.xml", url="http://x/a", size=1, entry_id="one")
        b = FileEntry(name="a.xml", url="http://x/a", size=1, entry_id="two")
        self.assertEqual(a.listing_hash(), b.listing_hash())


class TestParsePublishedAt(unittest.TestCase):
    """Each scraper supplies one format; samples from live UIs on 2026-09-09."""

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        fo = DiskFileOutput(cls._tmpdir.name)
        cls.bina = Bareket(file_output=fo)
        cls.shufersal = Shufersal(file_output=fo)
        cls.super_pharm = SuperPharm(file_output=fo)
        cls.hazi_hinam = HaziHinam(file_output=fo)
        cls.city_market_shops = CityMarketShops(file_output=fo)
        cls.publishprice = Mega(file_output=fo)
        cls.meshnat = MeshnatYosef1(file_output=fo)
        cls.victory_new = VictoryNewSource(file_output=fo)
        cls.matrix = Victory(file_output=fo)
        cls.netiv = NetivHased(file_output=fo)

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def test_bina_datefile(self):
        """Bina listing timestamps are ``HH:MM DD/MM/YYYY``."""
        self.assertEqual(self.bina.listing_date_key, "DateFile")
        self.assertEqual(
            FileEntry.parse_published_at(
                "14:18 08/09/2026", self.bina.listing_date_format
            ),
            "2026-09-08T14:18:00",
        )

    def test_shufersal_update_time(self):
        """Shufersal uses MultiPageWeb's ``M/D/YYYY h:mm:ss AM/PM`` format."""
        # Shufersal does not override; MultiPageWeb.__init__ sets this default.
        self.assertEqual(self.shufersal.listing_date_format, "%m/%d/%Y %I:%M:%S %p")
        self.assertEqual(
            FileEntry.parse_published_at(
                "9/8/2026 2:00:00 AM", self.shufersal.listing_date_format
            ),
            "2026-09-08T02:00:00",
        )

    def test_super_pharm_mdy(self):
        """Super Pharm listing timestamps are ``MM/DD/YYYY HH:MM:SS``."""
        self.assertEqual(
            FileEntry.parse_published_at(
                "09/08/2026 19:40:10", self.super_pharm.listing_date_format
            ),
            "2026-09-08T19:40:10",
        )

    def test_hazi_hinam_and_city_market(self):
        """Hazi Hinam and City Market Shops share ``DD-MM-YYYY HH:MM``."""
        self.assertEqual(
            self.hazi_hinam.listing_date_format,
            self.city_market_shops.listing_date_format,
        )
        self.assertEqual(
            FileEntry.parse_published_at(
                "09-09-2026 00:20", self.hazi_hinam.listing_date_format
            ),
            "2026-09-09T00:20:00",
        )
        self.assertEqual(
            FileEntry.parse_published_at(
                "08-09-2026 23:50", self.city_market_shops.listing_date_format
            ),
            "2026-09-08T23:50:00",
        )

    def test_publishprice_modified(self):
        """PublishPrice listing timestamps are ``HH:MM DD-MM-YYYY``."""
        self.assertEqual(
            FileEntry.parse_published_at(
                "00:01 09-09-2026", self.publishprice.listing_date_format
            ),
            "2026-09-09T00:01:00",
        )

    def test_meshnat_iso_date(self):
        """Meshmat Yosef listing timestamps are ``YYYY-MM-DD HH:MM:SS``."""
        self.assertEqual(
            FileEntry.parse_published_at(
                "2026-09-09 00:00:00", self.meshnat.listing_date_format
            ),
            "2026-09-09T00:00:00",
        )

    def test_victory_file_date(self):
        self.assertEqual(
            FileEntry.parse_published_at(
                "2026-09-11 22:30:37", self.victory_new.listing_date_format
            ),
            "2026-09-11T22:30:37",
        )

    def test_matrix_td_date(self):
        self.assertEqual(
            FileEntry.parse_published_at(
                "11/09/2026 06:27:02", self.matrix.listing_date_format
            ),
            "2026-09-11T06:27:02",
        )

    def test_netiv_file_date(self):
        self.assertEqual(
            FileEntry.parse_published_at(
                "11/09/2026 14:23", self.netiv.listing_date_format
            ),
            "2026-09-11T14:23:00",
        )

    def test_ftp_mlsd_modify(self):
        self.assertEqual(
            _ftp_mlsd_published_at({"modify": "20260911143037"}),
            "2026-09-11T14:30:37",
        )
        self.assertIsNone(_ftp_mlsd_published_at({}))

    def test_wrong_format_is_none(self):
        """A scraper must not try every format; mismatch stays None."""
        self.assertIsNone(
            FileEntry.parse_published_at(
                "14:18 08/09/2026", self.shufersal.listing_date_format
            )
        )
        self.assertIsNone(
            FileEntry.parse_published_at(None, self.bina.listing_date_format)
        )
        self.assertIsNone(
            FileEntry.parse_published_at(
                "PromoFull7290058249350-000-043-20260909-000051.gz",
                self.bina.listing_date_format,
            )
        )
