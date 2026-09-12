"""Data type for file entries flowing through the scraper pipeline."""

import hashlib
from datetime import datetime
from typing import NamedTuple, Optional


class FileEntry(NamedTuple):
    """
    Encapsulates a file listing: name, url, size, and optional publish time.

    Used by AsyncGenerators throughout the engine pipeline instead of raw tuples.
    ``published_at`` is ISO ``YYYY-MM-DDTHH:MM:SS`` from the site when present.
    """

    name: str
    url: Optional[str]
    size: Optional[int]
    published_at: Optional[str] = None

    def listing_hash(self) -> str:
        """Stable sha256 of listing identity (name, url, size).

        Publish time is not part of identity: site date formats vary and must
        not cause a re-download. It is used at save time to keep the newer file.
        """
        size = "" if self.size is None else str(self.size)
        payload = f"{self.name}\n{self.url}\n{size}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def parse_published_at(raw, fmt):
        """Parse one listing date with the caller's format. No format scanning."""
        if not raw or not fmt:
            return None
        try:
            parsed = datetime.strptime(" ".join(str(raw).split()), fmt)
        except ValueError:
            return None
        return parsed.strftime("%Y-%m-%dT%H:%M:%S")
