"""file_to_download forces a verified file to be downloaded and re-queued."""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from il_supermarket_scarper.engines.engine import Engine
from il_supermarket_scarper.utils import (
    AbstractQueueHandler,
    DumpFolderNames,
    FileEntry,
    QueueFileOutput,
    SaveDecision,
)
from il_supermarket_scarper.utils.databases import JsonDataBase
from il_supermarket_scarper.utils.scraping.scraper_status_contract import (
    ScraperStatusOutput,
)
from il_supermarket_scarper.utils.scraping.state import FilterState

PRICE = "Price7290027600007-001-202609070100"
PROMO = "Promo7290027600007-001-202609070100"
OLD_PRICE = "Price7290027600007-001-202609050100"


class _ListQueue(AbstractQueueHandler):
    """Collects queued file names in a list."""

    def __init__(self):
        self.sent = []

    async def send(self, message):
        self.sent.append(message["file_name"])

    def get_queue_name(self):
        return "list"

    async def close(self):
        """Nothing to release."""

    def close_sync(self):
        """Nothing to release."""


class _OfflineEngine(Engine):
    """Lists fixed names and 'downloads' constant XML bytes."""

    def __init__(self, tmp, names):
        self.queue = _ListQueue()
        super().__init__(
            chain=DumpFolderNames.SHUFERSAL,
            chain_id="7290027600007",
            file_output=QueueFileOutput(self.queue, storage_path=tmp),
            status_database=JsonDataBase("shufersal_force", tmp),
        )
        self.names = names

    async def collect_files_details_from_site(  # pylint: disable=too-many-arguments
        self,
        state,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        file_name_regex=None,
        filter_null=False,
        filter_zero=False,
        min_size=None,
        max_size=None,
        random_selection=False,
    ):  # pylint: disable=unused-argument
        async def listed():
            for name in self.names:
                yield FileEntry(
                    name=f"{name}.xml", url=f"http://example.test/{name}", size=1
                )

        async for entry in self.apply_limit(
            state,
            self.register_all_saw_files_on_site(listed()),
            limit=limit,
            files_types=files_types,
            when_date=when_date,
            file_name_regex=file_name_regex,
        ):
            yield entry

    async def process_file(self, file_details):
        self.status.register_collected_file(
            file_name_collected_from_site=file_details.name,
            link_collected_from_site=file_details.url,
            entry_id=file_details.entry_id,
        )
        return await self._finalize_extracted_content(
            file_details, b"<Root><Items/></Root>", file_details.name
        )


async def _scrape(engine, **kwargs):
    return [result async for result in engine.scrape(**kwargs)]


class TestFileToDownload(unittest.IsolatedAsyncioTestCase):
    """Verified files are skipped unless requested through file_to_download."""

    async def test_forced_file_is_downloaded_and_requeued(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _OfflineEngine(tmp, [PRICE, PROMO])
            await _scrape(engine)
            self.assertEqual(
                sorted(engine.queue.sent), [f"{PRICE}.xml", f"{PROMO}.xml"]
            )

            engine.queue.sent.clear()
            self.assertEqual(await _scrape(engine), [])
            self.assertEqual(engine.queue.sent, [])

            results = await _scrape(engine, file_to_download=[f"{PRICE}.gz"])
            self.assertEqual([r.file_name for r in results], [f"{PRICE}.xml"])
            self.assertEqual(results[0].save_decision, SaveDecision.FORCED)
            self.assertEqual(engine.queue.sent, [f"{PRICE}.xml"])

            started = [
                doc
                for doc in engine.status.database.list_documents("global_status")
                if doc["status"] == "started"
            ]
            self.assertIsNone(started[0]["file_to_download"])
            self.assertEqual(started[-1]["file_to_download"], [PRICE])

    async def test_forced_rerun_with_limit_keeps_status_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _OfflineEngine(tmp, [PRICE, PROMO])
            await _scrape(engine, limit=1)
            first = engine.queue.sent[0].replace(".xml", "")
            await _scrape(engine, limit=1, file_to_download=[first])

            (status_file,) = Path(tmp).glob("*.json")
            status = ScraperStatusOutput(**json.loads(status_file.read_text()))
            self.assertEqual(len(engine.queue.sent), 3)
            self.assertTrue(status.validate_file_status())

    async def test_forced_file_ignores_date_and_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _OfflineEngine(tmp, [PRICE, OLD_PRICE, PROMO])
            engine._forced_names = {OLD_PRICE}  # pylint: disable=protected-access
            engine._forced_pending = {OLD_PRICE}  # pylint: disable=protected-access

            async def listed():
                for name in engine.names:
                    yield FileEntry(
                        name=name, url=f"http://example.test/{name}", size=1
                    )

            state = FilterState()
            kept = [
                entry.name
                async for entry in engine.apply_limit(
                    state, listed(), limit=1, when_date=datetime(2026, 9, 7)
                )
            ]

            self.assertEqual(kept, [PRICE, OLD_PRICE])
            self.assertEqual(state.file_pass_limit, 1)

    async def test_unlisted_forced_file_is_left_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _OfflineEngine(tmp, [PRICE])
            results = await _scrape(engine, file_to_download=[OLD_PRICE])

            self.assertEqual([r.file_name for r in results], [f"{PRICE}.xml"])
            self.assertEqual(
                engine._forced_pending, {OLD_PRICE}  # pylint: disable=protected-access
            )


if __name__ == "__main__":
    unittest.main()
