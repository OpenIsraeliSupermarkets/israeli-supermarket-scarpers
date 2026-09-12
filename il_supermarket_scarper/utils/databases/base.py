from abc import ABC, abstractmethod
from typing import Dict, Optional


class AbstractDataBase(ABC):
    """Abstract base class for database operations.

    Verified-download rows keep an in-process index updated on every insert so
    callers never maintain a parallel cache to sync.
    """


    def __init__(self, database_name) -> None:
        self.database_name = database_name.replace(" ", "_").lower()
        # None => not loaded yet; load lazily from durable docs, then write-through.
        self._verified_listing_hashes: Optional[set] = None
        self._saved_by_name: Optional[Dict[str, Dict[str, Optional[str]]]] = None

    def get_database_name(self):
        """Get the name of the database."""
        return self.database_name

    def insert_document(self, collection_name, document):
        """Insert a document; refresh verified indexes when applicable."""
        self._do_insert_document(collection_name, document)
        if collection_name == ScraperStatus.VERIFIED_DOWNLOADS:
            self._on_verified_insert(document)

    def insert_documents(self, collection_name, documents):
        """Insert many documents; refresh verified indexes when applicable."""
        self._do_insert_documents(collection_name, documents)
        if collection_name == self.VERIFIED_DOWNLOADS:
            for document in documents:
                self._on_verified_insert(document)

    @abstractmethod
    def _do_insert_document(self, collection_name, document):
        """Persist a single document."""

    def _do_insert_documents(self, collection_name, documents):
        """Persist many documents (default: one-by-one without double-indexing)."""
        for document in documents:
            self._do_insert_document(collection_name, document)

    def _on_verified_insert(self, document) -> None:
        """Write-through the verified index after a durable insert."""
        if self._verified_listing_hashes is None:
            # Include the row just written via list_documents.
            self._ensure_verified_index()
            return
        self._index_verified_doc(document)

    def _ensure_verified_index(self) -> None:
        """Load verified_downloads once into O(1) listing/name indexes."""
        if self._verified_listing_hashes is not None:
            return
        self._verified_listing_hashes = set()
        self._saved_by_name = {}
        for doc in self.list_documents(ScraperStatus.VERIFIED_DOWNLOADS):
            self._index_verified_doc(doc)

    def _index_verified_doc(self, doc) -> None:
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

    def has_verified_listing(self, listing_hash: str) -> bool:
        """True if this listing_hash was stored in verified_downloads."""
        if not listing_hash:
            return False
        self._ensure_verified_index()
        return listing_hash in self._verified_listing_hashes

    def known_file(self, file_name: str) -> Optional[Dict[str, Optional[str]]]:
        """Return ``{content_sha256, published_at}`` for a stored file name."""
        self._ensure_verified_index()
        return self._saved_by_name.get(file_name)

    def find_document(self, collection_name, query):  # pylint: disable=unused-argument
        """Return the first matching document, or None."""
        return None

    def list_documents(self, collection_name):  # pylint: disable=unused-argument
        """Return all documents in a collection (empty list if missing)."""
        return []

    @abstractmethod
    def get_last_modified(self):
        """Get the last modified timestamp when scraper last wrote to this database."""

    @abstractmethod
    def _update_last_modified(self):
        """Update the last modified timestamp to current time."""
