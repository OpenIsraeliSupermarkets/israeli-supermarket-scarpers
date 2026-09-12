"""Abstract file output interface for saving scraped files."""

import asyncio
import hashlib
import multiprocessing
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any, Dict, AsyncGenerator, Optional, Tuple
import os
from .logger import Logger
from .gzip_utils import extract_xml_from_gz_in_memory, is_compressed_content


class SaveDecision(str, Enum):
    """How FileOutput resolved a repeated file name.

    Parsers split ``FileNm`` for type, chain, store, and date. Never suffix
    or rename; keep the original name and overwrite or re-queue in place.
    """

    CREATED = "created"  # first time this name is stored
    REWROTE_SAME = "rewrote_same"  # same name, same sha256; skip write/send
    HASH_MISMATCH = "hash_mismatch"  # same name, different sha256; overwrite / re-queue
    STALE_OLDER = "stale_older"  # same name, older published_at; keep the newer file


def content_sha256(content: bytes) -> str:
    """Hex digest of file bytes."""
    return hashlib.sha256(content).hexdigest()


class FileOutput(ABC):
    """Abstract base class for file output handlers."""

    def __init__(self):
        self._saved_digests: Dict[str, str] = {}
        self._saved_published_at: Dict[str, str] = {}
        self._save_locks: Dict[str, asyncio.Lock] = {}
        self._save_locks_guard = asyncio.Lock()

    async def _lock_for_name(self, file_name: str) -> asyncio.Lock:
        """Serialize saves that share an extracted file name."""
        async with self._save_locks_guard:
            lock = self._save_locks.get(file_name)
            if lock is None:
                lock = asyncio.Lock()
                self._save_locks[file_name] = lock
            return lock

    @asynccontextmanager
    async def _locked_save_decision(
        self,
        file_name: str,
        file_content: bytes,
        published_at: Optional[str] = None,
    ):
        """Hold the per-name lock and yield (name, decision, digest)."""
        lock = await self._lock_for_name(file_name)
        async with lock:
            yield self.resolve_save_name(file_name, file_content, published_at)

    def resolve_save_name(
        self,
        file_name: str,
        content: bytes,
        published_at: Optional[str] = None,
    ) -> Tuple[str, SaveDecision, str]:
        """Keep ``file_name``. Compare sha256 against this scrape's memory.

        Same hash is a no-op. Different hash is ``HASH_MISMATCH``: callers
        overwrite the disk file or push the queue again, then remember the
        new digest. An older ``published_at`` does not replace a newer file.
        Digest is stored only after a successful write/send.
        """
        digest = content_sha256(content)
        known = self._saved_digests.get(file_name)
        if known is None:
            return file_name, SaveDecision.CREATED, digest
        stored_published = self._saved_published_at.get(file_name)
        if (
            published_at
            and stored_published
            and published_at < stored_published
        ):
            Logger.info(
                f"{file_name} listed at {published_at} is older than "
                f"already stored {stored_published}; keeping the newer file"
            )
            return file_name, SaveDecision.STALE_OLDER, digest
        if known == digest:
            return file_name, SaveDecision.REWROTE_SAME, digest
        Logger.info(
            f"{file_name} already stored with sha256={known}; "
            f"downloaded sha256={digest}; overwriting / re-queueing"
        )
        return file_name, SaveDecision.HASH_MISMATCH, digest

    def _should_persist(self, save_decision: SaveDecision) -> bool:
        """True when bytes should be written or sent (not a same-hash no-op)."""
        return save_decision in (SaveDecision.CREATED, SaveDecision.HASH_MISMATCH)

    def _remember_digest(
        self,
        file_name: str,
        digest: str,
        published_at: Optional[str] = None,
        save_decision: Optional[SaveDecision] = None,
    ) -> None:
        """Record sha256 and publish time after a successful write or skip-same."""
        if save_decision == SaveDecision.STALE_OLDER:
            return
        if self._should_persist(save_decision) or save_decision is None:
            self._saved_digests[file_name] = digest
        if published_at:
            known = self._saved_published_at.get(file_name)
            if known is None or published_at >= known:
                self._saved_published_at[file_name] = published_at

    @abstractmethod
    async def save_file(
        self,
        file_link: str,
        file_name: str,
        file_content: bytes,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Save a file and return status information.

        Args:
            file_link: The URL where the file was downloaded from
            file_name: The name of the file
            file_content: The raw file content as bytes
            metadata: Optional metadata about the file (chain_id, store_id, etc.)

        Returns:
            Dict with keys: file_name, saved, error, metadata
        """

    async def _extract_if_compressed(
        self, file_content: bytes, file_name: str, extract_gz: bool = True
    ) -> Tuple[bytes, str, bool, Optional[str]]:
        """
        Extract compressed content if needed.

        Detects compression by content magic bytes (gzip: 0x1f8b, zip: PK)
        rather than filename extension, since some servers return compressed
        content under filenames without .gz extension.

        Returns:
            (content, filename, extraction_success, error)
        """
        if not extract_gz or not is_compressed_content(file_content):
            return file_content, file_name, True, None

        try:
            extracted = await asyncio.to_thread(
                extract_xml_from_gz_in_memory, file_content, file_name
            )
            base_name = file_name[:-3] if file_name.endswith(".gz") else file_name
            new_name = os.path.splitext(base_name)[0] + ".xml"
            return extracted, new_name, True, None
        except Exception as e:  # pylint: disable=broad-except
            Logger.error(f"Failed to extract {file_name}: {e}")
            return file_content, file_name, False, str(e)

    @abstractmethod
    def make_sure_accassible(self):
        """create the storage path"""

    @abstractmethod
    def get_output_location(self) -> str:
        """Get a string representation of where files are being saved."""

    @abstractmethod
    def get_storage_path(self) -> str:
        """Get the file system path for storing status files and metadata."""

    @abstractmethod
    async def close(self):
        """Close the file output."""

    def close_sync(self):
        """Close the file output synchronously (no-op for non-queue outputs)."""


class DiskFileOutput(FileOutput):
    """Save files to disk (current default behavior)."""

    def __init__(self, storage_path: str, extract_gz: bool = True):
        """
        Initialize disk file output.

        Args:
            storage_path: Path where files should be saved
            extract_gz: Whether to extract .gz files after downloading
        """
        self.storage_path = storage_path
        self.extract_gz = extract_gz
        os.makedirs(storage_path, exist_ok=True)
        super().__init__()

    async def save_file(
        self,
        file_link: str,
        file_name: str,
        file_content: bytes,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Decompress file if needed and write final content to disk."""
        saved = False
        extract_successfully = False
        error = None
        digest = None
        save_decision = None

        try:
            # Extract if it's compressed
            file_content, file_name, extract_successfully, extract_error = (
                await self._extract_if_compressed(
                    file_content, file_name, self.extract_gz
                )
            )
            if not extract_successfully:
                error = extract_error

            published_at = (metadata or {}).get("published_at")
            async with self._locked_save_decision(
                file_name, file_content, published_at
            ) as (file_name, save_decision, digest):
                file_save_path = os.path.join(self.storage_path, file_name)
                if self._should_persist(save_decision):
                    await asyncio.to_thread(
                        self._write_file, file_save_path, file_content
                    )
                self._remember_digest(
                    file_name, digest, published_at, save_decision
                )

            saved = True
            Logger.debug(
                f"Saved {file_link} to {file_save_path} sha256={digest} "
                f"save_decision={save_decision}"
            )

        except Exception as exception:  # pylint: disable=broad-except
            Logger.error(f"Error saving {file_link} to disk: {exception}")
            Logger.error_execption(exception)
            error = str(exception)
            digest = None
            save_decision = None

        return {
            "file_name": file_name,
            "saved": saved,
            "extract_successfully": extract_successfully,
            "error": error,
            "content_sha256": digest,
            "save_decision": save_decision,
            "metadata": metadata or {},
        }

    def make_sure_accassible(self):
        """create the storage path"""
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def _write_file(self, file_path: str, content: bytes):
        """Write bytes to file (sync operation for thread)."""
        with open(file_path, "wb") as f:
            f.write(content)

    def get_output_location(self) -> str:
        """Return the disk storage path."""
        return f"disk:{self.storage_path}"

    def get_storage_path(self) -> str:
        """Return the storage path for status files and metadata."""
        return self.storage_path

    async def close(self):
        """Close the file output."""


class QueueFileOutput(FileOutput):
    """Send files to an abstract queue."""

    def __init__(
        self,
        queue_handler: "AbstractQueueHandler",
        storage_path: str = "/tmp/il_supermarket_status",
        extract_gz: bool = True,
    ):
        """
        Initialize queue file output.

        Args:
            queue_handler: An implementation of AbstractQueueHandler
            storage_path: Path for storing status files (default: /tmp/il_supermarket_status)
            extract_gz: Whether to extract compressed files before sending to queue
        """
        self.queue_handler: AbstractQueueHandler = queue_handler
        self.storage_path = storage_path
        self.extract_gz = extract_gz
        os.makedirs(storage_path, exist_ok=True)
        super().__init__()

    async def save_file(
        self,
        file_link: str,
        file_name: str,
        file_content: bytes,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Send file to queue, extracting compressed files first."""
        saved = False
        extract_successfully = False
        error = None
        digest = None
        save_decision = None

        try:
            # Extract if it's compressed (detected by magic bytes)
            file_content, file_name, extract_successfully, extract_error = (
                await self._extract_if_compressed(
                    file_content, file_name, self.extract_gz
                )
            )
            if not extract_successfully:
                error = extract_error
            if extract_successfully:
                published_at = (metadata or {}).get("published_at")
                async with self._locked_save_decision(
                    file_name, file_content, published_at
                ) as (file_name, save_decision, digest):
                    if self._should_persist(save_decision):
                        message = {
                            "file_name": file_name,
                            "file_link": file_link,
                            "file_content": file_content,
                            "content_sha256": digest,
                            "save_decision": save_decision,
                            "metadata": metadata or {},
                        }
                        await self.queue_handler.send(message)
                    self._remember_digest(
                        file_name, digest, published_at, save_decision
                    )
                saved = True
                Logger.debug(
                    f"Queue {file_name} sha256={digest} "
                    f"save_decision={save_decision}"
                )

        except Exception as exception:  # pylint: disable=broad-except
            Logger.error(f"Error sending {file_link} to queue: {exception}")
            Logger.error_execption(exception)
            error = str(exception)
            digest = None
            save_decision = None

        return {
            "file_name": file_name,
            "saved": saved,
            "extract_successfully": extract_successfully,
            "error": error,
            "content_sha256": digest,
            "save_decision": save_decision,
            "metadata": metadata or {},
        }

    def get_output_location(self) -> str:
        """Return the queue location."""
        return f"queue:{self.queue_handler.get_queue_name()}"

    def get_storage_path(self) -> str:
        """Return the storage path for status files and metadata."""
        return self.storage_path

    def make_sure_accassible(self):
        """create the storage path"""
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    async def close(self):
        """Close the file output."""
        await self.queue_handler.close()
        Logger.debug("Queue handler closed")

    def close_sync(self):
        """Close the queue handler synchronously to unblock any waiting consumers."""
        self.queue_handler.close_sync()
        Logger.debug("Queue handler closed (sync)")


class AbstractQueueHandler(ABC):
    """Abstract base class for queue handlers."""

    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> None:
        """
        Send a message to the queue.

        Args:
            message: Dictionary containing file_name, file_link, file_content, metadata
        """
        raise NotImplementedError

    @abstractmethod
    def get_queue_name(self) -> str:
        """Return the name/identifier of the queue."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close the queue connection."""
        raise NotImplementedError

    @abstractmethod
    def close_sync(self) -> None:
        """Close the queue connection synchronously."""
        raise NotImplementedError


class InMemoryQueueHandler(AbstractQueueHandler):
    """
    Process-safe in-memory queue for testing.
    Not suitable for production - data is lost on restart.

    Messages can be consumed as they arrive using the async generator
    returned by get_all_messages(). Works across threads and processes.
    """

    # Shared manager for creating proxy queues
    _manager = None

    @classmethod
    def _get_manager(cls):
        if cls._manager is None:
            cls._manager = multiprocessing.Manager()
        return cls._manager

    def __init__(self, queue_name: str = "default"):
        """
        Initialize in-memory queue.

        Args:
            queue_name: Name of the queue
        """
        self.queue_name = queue_name
        # Use Manager queue which can be pickled and shared across processes
        self._queue = self._get_manager().Queue()

    async def send(self, message: Dict[str, Any]) -> None:
        """Add message to queue (process-safe)."""
        self._queue.put(message)
        Logger.debug(f"Added message to in-memory queue: {message['file_name']}")

    def get_queue_name(self) -> str:
        """Return queue name."""
        return f"memory:{self.queue_name}"

    async def close(self) -> None:
        """Signal that no more messages will be sent."""
        self._queue.put(None)

    def close_sync(self) -> None:
        """Signal that no more messages will be sent (synchronous version)."""
        self._queue.put(None)

    async def get_all_messages(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Async generator that yields messages as they arrive.
        Stops when close() is called. Process-safe.
        """
        loop = asyncio.get_event_loop()
        while True:
            # Run blocking get() in thread pool to not block event loop
            message = await loop.run_in_executor(None, self._queue.get)
            if message is None:
                break
            yield message
