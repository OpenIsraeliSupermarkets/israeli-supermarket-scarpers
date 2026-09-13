"""VerifiedDownloads indexes and SavePolicy decisions."""

import tempfile
import unittest

from il_supermarket_scarper.utils import DiskFileOutput, FileEntry, content_sha256
from il_supermarket_scarper.utils.databases import JsonDataBase
from il_supermarket_scarper.utils.files.save_policy import SaveDecision, SavePolicy
from il_supermarket_scarper.utils.scraping.scraper_status import ScraperStatus
from il_supermarket_scarper.utils.files.verified_downloads import VerifiedDownloads


class TestVerifiedDownloadsAndSavePolicy(unittest.IsolatedAsyncioTestCase):
    """Hydrate once; decide from verified digests/published_at across scrapes."""

    def _fixtures(self, tmp):
        """Status + verified + save-policy wired to one temp JsonDataBase."""
        output = DiskFileOutput(tmp)
        db = JsonDataBase("status_idx", tmp)
        status = ScraperStatus("status_idx", status_database=db, file_output=output)
        verified = VerifiedDownloads(db)
        return status, verified, SavePolicy(verified), db

    def test_hydrate_listing_hash_skip(self):
        """Prior verified listing_hash skips the same listing."""
        with tempfile.TemporaryDirectory() as tmp:
            _status, verified, _policy, db = self._fixtures(tmp)
            entry = FileEntry(name="PromoFull7290-001", url="http://x/a", size=1)
            db.insert_document(
                VerifiedDownloads.COLLECTION,
                {
                    "file_name": "PromoFull7290-001.xml",
                    "listing_hash": entry.listing_hash(),
                    "content_sha256": "abc",
                    "task_id": "prev",
                },
            )
            self.assertTrue(verified.has_verified_listing(entry.listing_hash()))

    def test_resolve_rewrote_same_across_hydrate(self):
        """Same digest after hydrate yields REWROTE_SAME."""
        with tempfile.TemporaryDirectory() as tmp:
            _status, _verified, policy, db = self._fixtures(tmp)
            payload = b"<xml>same</xml>"
            digest = content_sha256(payload)
            db.insert_document(
                VerifiedDownloads.COLLECTION,
                {
                    "file_name": "PromoFull7290-001.xml",
                    "listing_hash": "h1",
                    "content_sha256": digest,
                    "published_at": "2026-09-08T14:00:00",
                    "task_id": "prev",
                },
            )
            decision = policy.resolve_save_decision(
                "PromoFull7290-001.xml", digest, "2026-09-08T15:00:00"
            )
            self.assertEqual(decision, SaveDecision.REWROTE_SAME)

    def test_resolve_stale_older_across_hydrate(self):
        """Older published_at yields STALE_OLDER."""
        with tempfile.TemporaryDirectory() as tmp:
            _status, _verified, policy, db = self._fixtures(tmp)
            db.insert_document(
                VerifiedDownloads.COLLECTION,
                {
                    "file_name": "PromoFull7290-001.xml",
                    "listing_hash": "h1",
                    "content_sha256": "olddigest",
                    "published_at": "2026-09-08T14:00:00",
                    "task_id": "prev",
                },
            )
            decision = policy.resolve_save_decision(
                "PromoFull7290-001.xml",
                "newdigest",
                "2026-09-08T10:00:00",
            )
            self.assertEqual(decision, SaveDecision.STALE_OLDER)

    def test_resolve_hash_mismatch_when_newer(self):
        """Newer published_at with new digest yields HASH_MISMATCH."""
        with tempfile.TemporaryDirectory() as tmp:
            _status, _verified, policy, db = self._fixtures(tmp)
            db.insert_document(
                VerifiedDownloads.COLLECTION,
                {
                    "file_name": "PromoFull7290-001.xml",
                    "listing_hash": "h1",
                    "content_sha256": "olddigest",
                    "published_at": "2026-09-08T10:00:00",
                    "task_id": "prev",
                },
            )
            decision = policy.resolve_save_decision(
                "PromoFull7290-001.xml",
                "newdigest",
                "2026-09-08T14:00:00",
            )
            self.assertEqual(decision, SaveDecision.HASH_MISMATCH)

    def test_resolve_hash_mismatch_without_dates(self):
        """Missing dates with new digest yield HASH_MISMATCH."""
        with tempfile.TemporaryDirectory() as tmp:
            _status, _verified, policy, db = self._fixtures(tmp)
            db.insert_document(
                VerifiedDownloads.COLLECTION,
                {
                    "file_name": "PromoFull7290-001.xml",
                    "listing_hash": "h1",
                    "content_sha256": "olddigest",
                    "task_id": "prev",
                },
            )
            decision = policy.resolve_save_decision(
                "PromoFull7290-001.xml", "newdigest", None
            )
            self.assertEqual(decision, SaveDecision.HASH_MISMATCH)

    async def test_decide_and_persist_skips_write_on_same_hash(self):
        """Second same-hash persist does not rewrite bytes."""
        with tempfile.TemporaryDirectory() as tmp:
            status, verified, policy, _db = self._fixtures(tmp)
            status.on_scraping_start(limit=None, files_types=None)
            verified.set_task_id(status.task_id)
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
        """filter_already_downloaded skips known listing hashes."""
        with tempfile.TemporaryDirectory() as tmp:
            _status, verified, _policy, db = self._fixtures(tmp)
            entry = FileEntry(name="PromoFull7290-001", url="http://x/a", size=1)
            other = FileEntry(name="PromoFull7290-001", url="http://x/b", size=1)
            db.insert_document(
                VerifiedDownloads.COLLECTION,
                {
                    "file_name": "PromoFull7290-001.xml",
                    "listing_hash": entry.listing_hash(),
                    "task_id": "prev",
                },
            )

            async def listed():
                yield entry
                yield other

            kept = []
            async for item in verified.filter_already_downloaded(listed()):
                kept.append(item)
            self.assertEqual(kept, [other])

    async def test_verified_row_uses_saved_file_name(self):
        """Verified rows store the extracted on-disk file name."""
        with tempfile.TemporaryDirectory() as tmp:
            status, verified, policy, db = self._fixtures(tmp)
            status.on_scraping_start(limit=None, files_types=None)
            verified.set_task_id(status.task_id)

            async def persist(_decision):
                return None

            await policy.decide_and_persist(
                "PromoFull7290-001.xml",
                "abc",
                None,
                persist,
                listing_hash=FileEntry(
                    name="PromoFull7290-001", url="http://x/a", size=1
                ).listing_hash(),
            )
            docs = db.list_documents(VerifiedDownloads.COLLECTION)
            self.assertEqual(docs[-1]["file_name"], "PromoFull7290-001.xml")
            self.assertTrue(
                verified.has_verified_listing(docs[-1]["listing_hash"])
            )

    async def test_entry_id_written_to_status_and_verified(self):
        """Saw/collected/downloaded/verified rows share the FileEntry entry_id."""
        with tempfile.TemporaryDirectory() as tmp:
            status, verified, policy, db = self._fixtures(tmp)
            status.on_scraping_start(limit=None, files_types=None)
            verified.set_task_id(status.task_id)
            entry = FileEntry(
                name="PromoFull7290-001", url="http://x/a", size=1, entry_id="story-9"
            )

            status.register_saw_file(
                file_name=entry.name,
                link=entry.url,
                size=entry.size,
                entry_id=entry.entry_id,
            )
            status.register_collected_file(
                file_name_collected_from_site=entry.name,
                link_collected_from_site=entry.url,
                entry_id=entry.entry_id,
            )

            async def persist(_decision):
                return None

            await policy.decide_and_persist(
                "PromoFull7290-001.xml",
                "abc",
                None,
                persist,
                listing_hash=entry.listing_hash(),
                entry_id=entry.entry_id,
            )

            events = db.list_documents("events")
            self.assertTrue(all(e.get("entry_id") == "story-9" for e in events))
            verified_docs = db.list_documents(VerifiedDownloads.COLLECTION)
            self.assertEqual(verified_docs[-1]["entry_id"], "story-9")
