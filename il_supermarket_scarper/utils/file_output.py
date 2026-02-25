"""Abstract file output interface for saving scraped files."""

import asyncio
import multiprocessing
from abc import ABC, abstractmethod
from typing import Any, Dict, AsyncGenerator
import os
from .logger import Logger
from .gzip_utils import extract_xml_from_gz_in_memory


class FileOutput(ABC):
    """Abstract base class for file output handlers."""

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
    ) -> tuple[bytes, str, bool]:
        """
        Extract compressed content if needed.

        Returns:
            (content, filename, extraction_success)
        """
        if not extract_gz or not file_name.endswith(".gz"):
            return file_content, file_name, True

        try:
            extracted = await asyncio.to_thread(
                extract_xml_from_gz_in_memory, file_content, file_name
            )
            new_name = os.path.splitext(file_name)[0] + '.xml'
            return extracted, new_name, True
        except Exception as e: # pylint: disable=broad-except
            Logger.error(f"Failed to extract {file_name}: {e}")
            return file_content, file_name, False

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

        try:
            # Extract if it's a .gz file
            file_content, file_name, extract_successfully = (
            await self._extract_if_compressed(file_content, file_name)
            )

            # Write file content to disk
            file_save_path = os.path.join(self.storage_path, file_name)
            await asyncio.to_thread(self._write_file, file_save_path, file_content)

            saved = True
            Logger.debug(f"Saved {file_link} to {file_save_path}")

        except Exception as exception:  # pylint: disable=broad-except
            Logger.error(f"Error saving {file_link} to disk: {exception}")
            Logger.error_execption(exception)
            error = str(exception)

        return {
            "file_name": file_name,
            "saved": saved,
            "extract_successfully": extract_successfully,
            "error": error,
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
    ):
        """
        Initialize queue file output.

        Args:
            queue_handler: An implementation of AbstractQueueHandler
            storage_path: Path for storing status files (default: /tmp/il_supermarket_status)
        """
        self.queue_handler: AbstractQueueHandler = queue_handler
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    async def save_file(
        self,
        file_link: str,
        file_name: str,
        file_content: bytes,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Send file to queue, extracting gzipped files first."""
        saved = False
        extract_successfully = False
        error = None

        try:
            # Extract if it's a .gz file
            file_content, file_name, extract_successfully = (
                await self._extract_if_compressed(file_content, file_name)
            )
            # Send file to queue
            if extract_successfully:
                message = {
                    "file_name": file_name,
                    "file_link": file_link,
                    "file_content": file_content,
                    "metadata": metadata or {},
                }

                await self.queue_handler.send(message)
                saved = True
                Logger.debug(f"Sent {file_name} to queue")

        except Exception as exception:  # pylint: disable=broad-except
            Logger.error(f"Error sending {file_link} to queue: {exception}")
            Logger.error_execption(exception)
            error = str(exception)

        return {
            "file_name": file_name,
            "saved": saved,
            "extract_successfully": extract_successfully,
            "error": error,
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
