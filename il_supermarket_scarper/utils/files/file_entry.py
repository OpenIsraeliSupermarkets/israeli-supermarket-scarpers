"""Data type for file entries flowing through the scraper pipeline."""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import FrozenSet, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Signed (pre-authorised) download links carry a signature and an expiry in the
# query string that the host rotates every few minutes (Shufersal's Azure blob
# links change about every 5 minutes). Those parameters say nothing about which
# file is listed, so they are left out of the listing identity.
#
# Each scheme is (marker, params, prefixes): the scheme applies only when the
# marker parameter is present, so ordinary URLs that happen to use a short
# name such as ``st`` or ``sp`` keep their full query and their old hash.
_SIGNED_URL_SCHEMES: Tuple[Tuple[str, FrozenSet[str], Tuple[str, ...]], ...] = (
    # Azure Storage SAS: ?sv=…&sr=b&sig=…&se=…&sp=r
    (
        "sig",
        frozenset(
            {
                "sv", "ss", "srt", "sr", "sp", "st", "se", "sip", "spr", "si",
                "sig", "sdd", "ses", "skoid", "sktid", "skt", "ske", "sks",
                "skv", "saoid", "suoid", "scid",
            }
        ),
        (),
    ),
    # AWS S3 presigned (SigV4): X-Amz-Signature, X-Amz-Expires, …
    ("x-amz-signature", frozenset(), ("x-amz-",)),
    # Legacy S3 presigned (SigV2): AWSAccessKeyId, Expires, Signature
    ("awsaccesskeyid", frozenset({"awsaccesskeyid", "expires", "signature"}), ()),
    # CloudFront signed URL: Expires|Policy, Signature, Key-Pair-Id
    (
        "key-pair-id",
        frozenset({"expires", "policy", "signature", "key-pair-id"}),
        (),
    ),
    # Google Cloud Storage signed URL (V4): X-Goog-Signature, X-Goog-Expires, …
    ("x-goog-signature", frozenset(), ("x-goog-",)),
)  # fmt: skip


def _identity_url(url: Optional[str]) -> Optional[str]:
    """URL as it identifies a listing: signed-URL parameters removed.

    A URL with no signature marker is returned unchanged (byte for byte), so
    chains without signed links keep the hashes already in their status DB.
    """
    if not url or "?" not in url:
        return url
    try:
        parts = urlsplit(url)
        pairs = parse_qsl(parts.query, keep_blank_values=True)
    except ValueError:
        return url
    keys = {key.lower() for key, _ in pairs}
    volatile = [
        (params, prefixes)
        for marker, params, prefixes in _SIGNED_URL_SCHEMES
        if marker in keys
    ]
    if not volatile:
        return url

    def is_volatile(key):
        key = key.lower()
        return any(
            key in params or key.startswith(prefixes) for params, prefixes in volatile
        )

    kept = [(key, value) for key, value in pairs if not is_volatile(key)]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment)
    )


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
        Signed-URL parameters (signature, expiry: Azure SAS, S3, CloudFront,
        GCS) are excluded too, because hosts rotate them every few minutes;
        name, path, the rest of the query and size still identify the file.
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
