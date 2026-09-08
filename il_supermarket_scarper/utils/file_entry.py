"""Data type for file entries flowing through the scraper pipeline."""

import hashlib
from typing import NamedTuple, Optional


class FileEntry(NamedTuple):
    """
    Encapsulates a file entry with name, url, and size.

    Used by AsyncGenerators throughout the engine pipeline instead of raw tuples.
    Preserves tuple unpacking: name, url, size = file_entry
    """

    name: str
    url: str
    size: Optional[int]

    def listing_hash(self) -> str:
        """Stable sha256 of listing identity (name, url, size)."""
        size = "" if self.size is None else str(self.size)
        payload = f"{self.name}\n{self.url}\n{size}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
