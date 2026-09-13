"""Verified-download registry: listing-hash skip and per-name digests."""

from typing import Dict, Optional, TYPE_CHECKING

from il_supermarket_scarper.utils.scraping.status import _now

if TYPE_CHECKING:
    from il_supermarket_scarper.utils.databases.base import AbstractDataBase
    from .save_policy import SaveDecision


class VerifiedDownloads:
    """Durable verified rows plus in-process listing/name indexes."""

    COLLECTION = "verified_downloads"

    def __init__(self, database: "AbstractDataBase") -> None:
        self.database = database
        self.task_id: Optional[str] = None
        # None => not loaded yet; load lazily from durable docs, then write-through.
        self._verified_listing_hashes: Optional[set] = None
        self._saved_by_name: Optional[Dict[str, Dict[str, Optional[str]]]] = None

    def set_task_id(self, task_id: Optional[str]) -> None:
        """Bind the current scrape task id for subsequent record() calls."""
        self.task_id = task_id

    def _ensure_index(self) -> None:
        """Load verified_downloads once into O(1) listing/name indexes."""
        if self._verified_listing_hashes is not None:
            return
        self._verified_listing_hashes = set()
        self._saved_by_name = {}
        for doc in self.database.list_documents(self.COLLECTION):
            self._index_doc(doc)

    def _index_doc(self, doc) -> None:
        """Merge one verified row into the in-process indexes."""
        assert self._verified_listing_hashes is not None
        assert self._saved_by_name is not None
        listing_hash = doc.get("listing_hash")
        if listing_hash:
            self._verified_listing_hashes.add(listing_hash)
        file_name = doc.get("file_name")
        if not file_name:
            return
        digest = doc.get("content_sha256")
        published_at = doc.get("published_at")
        known = self._saved_by_name.get(file_name)
        if known is None:
            self._saved_by_name[file_name] = {
                "content_sha256": digest,
                "published_at": published_at,
            }
            return
        stored_published = known.get("published_at")
        if published_at and (
            stored_published is None or published_at >= stored_published
        ):
            known["published_at"] = published_at
            if digest:
                known["content_sha256"] = digest
        elif known.get("content_sha256") is None and digest:
            known["content_sha256"] = digest

    def _on_insert(self, document) -> None:
        """Write-through the index after a durable insert."""
        if self._verified_listing_hashes is None:
            self._ensure_index()
            return
        self._index_doc(document)

    def has_verified_listing(self, listing_hash: str) -> bool:
        """True if this listing_hash was stored in verified_downloads."""
        if not listing_hash:
            return False
        self._ensure_index()
        return listing_hash in self._verified_listing_hashes

    def known_file(self, file_name: str) -> Optional[Dict[str, Optional[str]]]:
        """Return ``{content_sha256, published_at}`` for a stored file name."""
        self._ensure_index()
        return self._saved_by_name.get(file_name)

    def record(
        self,
        file_name: str,
        digest: Optional[str],
        published_at: Optional[str],
        save_decision: "SaveDecision",
        listing_hash: Optional[str] = None,
        entry_id: Optional[str] = None,
    ) -> None:
        """Persist a verified row and update indexes."""
        from .save_policy import SaveDecision  # pylint: disable=import-outside-toplevel

        decision_value = (
            save_decision.value
            if isinstance(save_decision, SaveDecision)
            else save_decision
        )
        document = {
            "file_name": file_name,
            "system_timestamp": _now(),
            "task_id": self.task_id,
            "content_sha256": digest,
            "save_decision": decision_value,
            "listing_hash": listing_hash,
            "published_at": published_at,
            "entry_id": entry_id,
        }
        self.database.insert_document(self.COLLECTION, document)
        self._on_insert(document)

    async def filter_already_downloaded(self, filelist, by_function=lambda x: x):
        """Skip listings already verified by listing_hash."""
        del by_function
        async for file in filelist:
            if not self.has_verified_listing(file.listing_hash()):
                yield file
