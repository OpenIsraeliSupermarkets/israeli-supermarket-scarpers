import asyncio
import os
import traceback
from typing import Dict, Optional
import uuid
from .status import log_folder_details, _now
from .databases import JsonDataBase, AbstractDataBase
from .file_output import FileOutput, SaveDecision, should_persist
from .logger import Logger
from .scraping_result import ScrapingResult


class ScraperStatus:
    """A class that abstracts the database interface for scraper status."""

    STARTED = "started"
    SAW = "saw"
    COLLECTED = "collected"
    DOWNLOADED = "downloaded"
    FAILED = "failed"
    ESTIMATED_SIZE = "estimated_size"
    VERIFIED_DOWNLOADS = "verified_downloads"

    def __init__(
        self,
        database_name,
        status_database: Optional[AbstractDataBase] = None,
        file_output: Optional[FileOutput] = None,
    ) -> None:
        # Use provided database or create default JsonDataBase
        if status_database is None:
            # Default: use JSON database in status subdirectory of file output path
            status_path = os.path.join(
                os.path.dirname(file_output.get_storage_path()), "status"
            )
            self.database = JsonDataBase(database_name, status_path)
        else:
            self.database = status_database
        self.task_id = None
        self._verified_listing_hashes: set = set()
        self._saved_by_name: Dict[str, Dict[str, Optional[str]]] = {}
        self._save_locks: Dict[str, asyncio.Lock] = {}
        self._save_locks_guard = asyncio.Lock()

    def on_scraping_start(self, limit, files_types, **additional_info):
        """Report that scraping has started."""
        self.task_id = str(uuid.uuid4())
        # Same-scrape indexes only; cross-scrape listing skip still hits the DB.
        self._verified_listing_hashes = set()
        self._saved_by_name = {}

        self._insert_global_status(
            ScraperStatus.STARTED,
            limit=limit,
            files_requested=files_types,
            **additional_info,
        )

    def register_saw_file(
        self,
        file_name,
        link,
        size,
        **additional_info,
    ):
        """Report that file details have been collected."""
        # Convert to comma-separated strings to match contract
        self._insert_event(
            ScraperStatus.SAW,
            file_name=file_name,
            link=link,
            size=size,
            **additional_info,
        )

    def register_collected_file(
        self,
        file_name_collected_from_site,
        link_collected_from_site=None,
        **additional_info,
    ):
        """Report that file details have been collected."""

        self._insert_event(
            ScraperStatus.COLLECTED,
            file_name=file_name_collected_from_site,
            link_collected=link_collected_from_site,
            **additional_info,
        )

    def register_downloaded_file(self, results: ScrapingResult):
        """Report that the file has been downloaded."""
        # Map results to contract field names
        event_data = {
            "file_name": results.file_name,
            "downloaded_successfully": results.downloaded,
            "extracted_successfully": results.extract_succefully,
            "error_message": results.error,
            "restart_and_retry": results.restart_and_retry,
            "content_sha256": results.content_sha256,
            "save_decision": results.save_decision,
        }
        self._insert_event(ScraperStatus.DOWNLOADED, **event_data)
        self._add_downloaded_files_to_list(results)

    def _is_verified_listing(self, file) -> bool:
        """True if this listing hash was already stored.

        Skip only by ``listing_hash``. Same FileNm with a different url or
        size is a new listing and must download. Rows without listing_hash
        (pre-clean DBs) do not skip. Same-scrape hits the in-memory set;
        otherwise query the status DB.
        """
        listing_hash = file.listing_hash()
        if listing_hash in self._verified_listing_hashes:
            return True
        return self.database.already_downloaded(
            self.VERIFIED_DOWNLOADS, {"listing_hash": listing_hash}
        )

    async def filter_already_downloaded(self, filelist, by_function=lambda x: x):
        """Skip listings already verified by listing_hash."""
        del by_function
        async for file in filelist:
            if not self._is_verified_listing(file):
                yield file

    async def _lock_for_name(self, file_name: str) -> asyncio.Lock:
        """Serialize save decisions that share an extracted file name."""
        async with self._save_locks_guard:
            lock = self._save_locks.get(file_name)
            if lock is None:
                lock = asyncio.Lock()
                self._save_locks[file_name] = lock
            return lock

    def resolve_save_decision(
        self,
        file_name: str,
        digest: str,
        published_at: Optional[str] = None,
    ) -> SaveDecision:
        """Decide whether to persist bytes for ``file_name``.

        Unknown name → CREATED. Older published_at → STALE_OLDER.
        Same digest → REWROTE_SAME. Else → HASH_MISMATCH.
        Missing dates allow overwrite when digests differ.
        """
        known = self._saved_by_name.get(file_name)
        if known is None:
            return SaveDecision.CREATED
        stored_published = known.get("published_at")
        if (
            published_at
            and stored_published
            and published_at < stored_published
        ):
            Logger.info(
                f"{file_name} listed at {published_at} is older than "
                f"already stored {stored_published}; keeping the newer file"
            )
            return SaveDecision.STALE_OLDER
        known_digest = known.get("content_sha256")
        if known_digest is not None and known_digest == digest:
            return SaveDecision.REWROTE_SAME
        Logger.info(
            f"{file_name} already stored with sha256={known_digest}; "
            f"downloaded sha256={digest}; overwriting / re-queueing"
        )
        return SaveDecision.HASH_MISMATCH

    def _remember_save(
        self,
        file_name: str,
        digest: str,
        published_at: Optional[str],
        save_decision: SaveDecision,
        listing_hash: Optional[str] = None,
    ) -> None:
        """Update in-memory indexes after a successful extract."""
        if listing_hash:
            self._verified_listing_hashes.add(listing_hash)
        if save_decision == SaveDecision.STALE_OLDER:
            return
        entry = self._saved_by_name.setdefault(
            file_name, {"content_sha256": None, "published_at": None}
        )
        if should_persist(save_decision) or entry.get("content_sha256") is None:
            entry["content_sha256"] = digest
        if published_at:
            known = entry.get("published_at")
            if known is None or published_at >= known:
                entry["published_at"] = published_at

    async def decide_and_persist(
        self,
        file_name: str,
        digest: str,
        published_at: Optional[str],
        persist,
        listing_hash: Optional[str] = None,
    ) -> SaveDecision:
        """Lock by name, decide, optionally persist, then update indexes.

        ``persist`` is only awaited when bytes must be written/sent; it need
        not receive the decision (caller already gated).
        """
        lock = await self._lock_for_name(file_name)
        async with lock:
            save_decision = self.resolve_save_decision(
                file_name, digest, published_at
            )
            if should_persist(save_decision):
                await persist()
            self._remember_save(
                file_name,
                digest,
                published_at,
                save_decision,
                listing_hash=listing_hash,
            )
            return save_decision

    def _add_downloaded_files_to_list(self, results: ScrapingResult):
        """Add downloaded files to the database collection."""
        if not results.extract_succefully:
            return
        listing_hash = results.file_entry.listing_hash()
        decision = (
            SaveDecision(results.save_decision)
            if results.save_decision
            else SaveDecision.CREATED
        )
        self._remember_save(
            results.file_name,
            results.content_sha256,
            results.file_entry.published_at,
            decision,
            listing_hash=listing_hash,
        )
        self.database.insert_document(
            self.VERIFIED_DOWNLOADS,
            {
                "file_name": results.file_name,
                "system_timestamp": _now(),
                "task_id": self.task_id,
                "content_sha256": results.content_sha256,
                "save_decision": results.save_decision,
                "listing_hash": listing_hash,
                "published_at": results.file_entry.published_at,
            },
        )

    def on_scrape_completed(
        self, folder_name: str, completed_successfully: bool = True
    ):
        """Report when scraping is completed."""
        self._insert_global_status(
            ScraperStatus.ESTIMATED_SIZE,
            folder_size=log_folder_details(folder_name),
            completed_successfully=completed_successfully,
        )

    def register_download_fail(self, error, file_name: str):
        """report when the scraping in failed"""
        # Map to contract field names
        self._insert_event(
            ScraperStatus.FAILED,
            error_message=str(error),
            traceback=traceback.format_exc(),
            file_name=file_name,
        )

    def _insert_global_status(self, status, **additional_info):
        """Insert a global status update (started, estimated_size)."""
        document = {
            "status": status,
            "system_timestamp": _now(),
            "task_id": self.task_id,
            **additional_info,
        }
        self.database.insert_document("global_status", document)

    def _insert_event(self, status, **additional_info):
        """Insert an event update (collected, downloaded, failed)."""
        document = {
            "status": status,
            "system_timestamp": _now(),
            "task_id": self.task_id,
            **additional_info,
        }
        self.database.insert_document("events", document)
