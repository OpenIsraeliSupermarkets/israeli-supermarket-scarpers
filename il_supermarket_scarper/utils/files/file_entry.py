"""Data type for file entries flowing through the scraper pipeline."""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

# Azure Blob Storage hosts sign their links with a SAS token in the query
# string (``?sv=…&sig=…&se=…``) that rotates every few minutes (Shufersal).
_SIGNED_BLOB_HOST_SUFFIX = ".blob.core.windows.net"


def _identity_url(url: Optional[str]) -> Optional[str]:
    """URL as it identifies a listing: drop the rotating SAS query on blob URLs.

    Every other URL is returned unchanged, so other chains' hashes stay the same.
    """
    if not url:
        return url
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
    except ValueError:
        return url
    if not host.endswith(_SIGNED_BLOB_HOST_SUFFIX):
        return url
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


@dataclass(frozen=True)
class FileEntry:
    """
    Encapsulates a file listing: name, url, size, and optional publish time.

    Used by AsyncGenerators throughout the engine pipeline instead of raw tuples.
    ``published_at`` is ISO ``YYYY-MM-DDTHH:MM:SS`` from the site when present.
    ``entry_id`` uniquely identifies one listing sighting / download story so the
    same FileNm can be traced across status events even when listed twice.
    """

    name: str
    url: Optional[str]
    size: Optional[int]
    published_at: Optional[str] = None
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def listing_hash(self) -> str:
        """Stable sha256 of listing identity (name, url, size).

        Publish time is not part of identity: site date formats vary and must
        not cause a re-download. It is used at save time to keep the newer file.
        ``entry_id`` is also excluded: it traces one story, not listing identity.
        On Azure blob URLs the query string (a SAS signature that rotates every
        few minutes) is excluded too; name, path and size still identify the file.
        """
        size = "" if self.size is None else str(self.size)
        url = _identity_url(self.url)
        payload = f"{self.name}\n{url}\n{size}".encode("utf-8")
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
