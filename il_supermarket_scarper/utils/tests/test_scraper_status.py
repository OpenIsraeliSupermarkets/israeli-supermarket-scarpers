"""ScraperStatus verified indexes and save decisions."""

import tempfile
import unittest

from il_supermarket_scarper.utils import DiskFileOutput, FileEntry, content_sha256
from il_supermarket_scarper.utils.databases import JsonDataBase
from il_supermarket_scarper.utils.save_policy import SaveDecision, SavePolicy
from il_supermarket_scarper.utils.scraper_status import ScraperStatus
from il_supermarket_scarper.utils.scraping_result import ScrapingResult


class TestScraperStatusIndexes(unittest.IsolatedAsyncioTestCase):
    """Hydrate once; decide from verified digests/published_at across scrapes."""

    def _status(self, tmp):
        output = DiskFileOutput(tmp)
        db = JsonDataBase("status_idx", tmp)
        status = ScraperStatus("status_idx", status_database=db, file_output=output)
        return status, SavePolicy(status), db

    def test_hydrate_listing_hash_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, _policy, db = self._status(tmp)
            entry = FileEntry(name="PromoFull7290-001", url="http://x/a", size=1)
            db.insert_document(
                ScraperStatus.VERIFIED_DOWNLOADS,
                {
                    "file_name": "PromoFull7290-001.xml",
                    "listing_hash": entry.listing_hash(),
                    "content_sha256": "abc",
                    "task_id": "prev",
                },
            )
            status.on_scraping_start(limit=None, files_types=None)
            self.assertTrue(
                status._is_verified_listing(entry)  # pylint: disable=protected-access
            )

    def test_resolve_rewrote_same_across_hydrate(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, policy, db = self._status(tmp)
            payload = b"<xml>same</xml>"
            digest = content_sha256(payload)
            db.insert_document(
                ScraperStatus.VERIFIED_DOWNLOADS,
                {
                    "file_name": "PromoFull7290-001.xml",
                    "listing_hash": "h1",
                    "content_sha256": digest,
                    "published_at": "2026-09-08T14:00:00",
                    "task_id": "prev",
                },
            )
            status.on_scraping_start(limit=None, files_types=None)
            decision = policy.resolve_save_decision(
                "PromoFull7290-001.xml", digest, "2026-09-08T15:00:00"
            )
            self.assertEqual(decision, SaveDecision.REWROTE_SAME)

    def test_resolve_stale_older_across_hydrate(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, policy, db = self._status(tmp)
            db.insert_document(
                ScraperStatus.VERIFIED_DOWNLOADS,
                {
                    "file_name": "PromoFull7290-001.xml",
                    "listing_hash": "h1",
                    "content_sha256": "olddigest",
                    "published_at": "2026-09-08T14:00:00",
                    "task_id": "prev",
                },
            )
            status.on_scraping_start(limit=None, files_types=None)
            decision = policy.resolve_save_decision(
                "PromoFull7290-001.xml",
                "newdigest",
                "2026-09-08T10:00:00",
            )
            self.assertEqual(decision, SaveDecision.STALE_OLDER)

    def test_resolve_hash_mismatch_when_newer(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, policy, db = self._status(tmp)
            db.insert_document(
                ScraperStatus.VERIFIED_DOWNLOADS,
                {
                    "file_name": "PromoFull7290-001.xml",
                    "listing_hash": "h1",
                    "content_sha256": "olddigest",
                    "published_at": "2026-09-08T10:00:00",
                    "task_id": "prev",
                },
            )
            status.on_scraping_start(limit=None, files_types=None)
            decision = policy.resolve_save_decision(
                "PromoFull7290-001.xml",
                "newdigest",
                "2026-09-08T14:00:00",
            )
            self.assertEqual(decision, SaveDecision.HASH_MISMATCH)

    def test_resolve_hash_mismatch_without_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, policy, db = self._status(tmp)
            db.insert_document(
                ScraperStatus.VERIFIED_DOWNLOADS,
                {
                    "file_name": "PromoFull7290-001.xml",
                    "listing_hash": "h1",
                    "content_sha256": "olddigest",
                    "task_id": "prev",
                },
            )
            status.on_scraping_start(limit=None, files_types=None)
            decision = policy.resolve_save_decision(
                "PromoFull7290-001.xml", "newdigest", None
            )
            self.assertEqual(decision, SaveDecision.HASH_MISMATCH)

    async def test_decide_and_persist_skips_write_on_same_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, policy, _db = self._status(tmp)
            status.on_scraping_start(limit=None, files_types=None)
            payload = b"<xml>x</xml>"
            digest = content_sha256(payload)
            writes = {"n": 0}

            async def persist(_decision):
                writes["n"] += 1

            first = await policy.decide_and_persist(
                "a.xml", digest, "2026-09-08T14:00:00", persist, listing_hash="lh1"
            )
            second = await policy.decide_and_persist(
                "a.xml", digest, "2026-09-08T15:00:00", persist, listing_hash="lh2"
            )
            self.assertEqual(first, SaveDecision.CREATED)
            self.assertEqual(second, SaveDecision.REWROTE_SAME)
            self.assertEqual(writes["n"], 1)

    async def test_filter_already_downloaded_uses_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, _policy, db = self._status(tmp)
            entry = FileEntry(name="PromoFull7290-001", url="http://x/a", size=1)
            other = FileEntry(name="PromoFull7290-001", url="http://x/b", size=1)
            db.insert_document(
                ScraperStatus.VERIFIED_DOWNLOADS,
                {
                    "file_name": "PromoFull7290-001.xml",
                    "listing_hash": entry.listing_hash(),
                    "task_id": "prev",
                },
            )
            status.on_scraping_start(limit=None, files_types=None)

            async def listed():
                yield entry
                yield other

            kept = []
            async for item in status.filter_already_downloaded(listed()):
                kept.append(item)
            self.assertEqual(kept, [other])

    def test_verified_row_uses_saved_file_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, _policy, db = self._status(tmp)
            status.on_scraping_start(limit=None, files_types=None)
            entry = FileEntry(name="PromoFull7290-001", url="http://x/a", size=1)
            status.register_downloaded_file(
                ScrapingResult(
                    file_entry=entry,
                    downloaded=True,
                    save_decision=SaveDecision.CREATED,
                    extract_succefully=True,
                    content_sha256="abc",
                    saved_file_name="PromoFull7290-001.xml",
                )
            )
            docs = db.list_documents(ScraperStatus.VERIFIED_DOWNLOADS)
            self.assertEqual(docs[-1]["file_name"], "PromoFull7290-001.xml")
            self.assertTrue(db.has_verified_listing(entry.listing_hash()))
