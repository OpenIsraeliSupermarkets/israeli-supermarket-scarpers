"""Save decisions for repeated FileNm values."""

import asyncio
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional

from .logger import Logger

if TYPE_CHECKING:
    from .scraper_status import ScraperStatus


class SaveDecision(str, Enum):
    """How a repeated file name was resolved before persist.

    Parsers split ``FileNm`` for type, chain, store, and date. Never suffix
    or rename; keep the original name and overwrite or re-queue in place.
    """

    CREATED = "created"  # first time this name is stored
    REWROTE_SAME = "rewrote_same"  # same name, same sha256; skip write/send
    HASH_MISMATCH = "hash_mismatch"  # same name, different sha256; overwrite / re-queue
    STALE_OLDER = "stale_older"  # same name, older published_at; keep the newer file


def should_persist(save_decision: SaveDecision) -> bool:
    """True when bytes should be written or sent (not a same-hash / stale no-op)."""
    return save_decision in (SaveDecision.CREATED, SaveDecision.HASH_MISMATCH)


class SavePolicy:
    """Decide whether to persist bytes; record verified rows via status."""

    def __init__(self, status: "ScraperStatus") -> None:
        self.status = status
        self._save_locks: Dict[str, asyncio.Lock] = {}
        self._save_locks_guard = asyncio.Lock()

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
        known = self.status.database.known_file(file_name)
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

    async def decide_and_persist(
        self,
        file_name: str,
        digest: str,
        published_at: Optional[str],
        persist,
        listing_hash: Optional[str] = None,
    ) -> SaveDecision:
        """Lock by name, decide, optionally persist, then record verified.

        ``persist`` is awaited with the ``SaveDecision`` when bytes must be
        written/sent.
        """
        lock = await self._lock_for_name(file_name)
        async with lock:
            save_decision = self.resolve_save_decision(
                file_name, digest, published_at
            )
            if should_persist(save_decision):
                await persist(save_decision)
            self.status.insert_verified_download(
                file_name,
                digest,
                published_at,
                save_decision,
                listing_hash=listing_hash,
            )
            return save_decision
