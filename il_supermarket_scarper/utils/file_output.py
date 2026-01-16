"""Abstract file output interface for saving scraped files."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict
import os
import gzip
import io
import zipfile
from .logger import Logger
from .gzip_utils import extract_xml_file_from_gz_file


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

    @abstractmethod
    def make_sure_accassible(self):
        """create the storage path"""

    @abstractmethod
    def get_output_location(self) -> str:
        """Get a string representation of where files are being saved."""

    @abstractmethod
    def get_storage_path(self) -> str:
        """Get the file system path for storing status files and metadata."""


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
        """Save file to disk and optionally extract if .gz."""
        saved = False
        extract_successfully = False
        error = None

        try:
            # Determine file path
            file_save_path = os.path.join(self.storage_path, file_name)

            # Add extension if needed
            if not (
                file_save_path.endswith(".gz") or file_save_path.endswith(".xml")
            ) and (file_link.endswith(".gz") or file_link.endswith(".xml")):
                file_save_path = (
                    file_save_path + "." + file_link.split("?")[0].split(".")[-1]
                )

            # Write file content to disk
            await asyncio.to_thread(self._write_file, file_save_path, file_content)
            saved = True

            # Extract if it's a .gz file
            if self.extract_gz and file_save_path.endswith("gz"):
                Logger.debug(f"File size is {os.path.getsize(file_save_path)} bytes.")
                await asyncio.to_thread(extract_xml_file_from_gz_file, file_save_path)
                await asyncio.to_thread(os.remove, file_save_path)
                extract_successfully = True
            else:
                extract_successfully = True

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
        self.queue_handler = queue_handler
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
            # Extract gzipped files in-memory before sending to queue
            if file_name.endswith(".gz"):
                try:
                    # Try gzip extraction first
                    file_content = gzip.decompress(file_content)
                    # Change extension from .gz to .xml
                    file_name = os.path.splitext(file_name)[0] + ".xml"
                    extract_successfully = True
                    Logger.debug(f"Extracted gzipped file to {file_name}")
                except (gzip.BadGzipFile, OSError):
                    # Try zip extraction as fallback
                    try:
                        with zipfile.ZipFile(io.BytesIO(file_content)) as the_zip:
                            zip_info = the_zip.infolist()[0]
                            with the_zip.open(zip_info) as the_file:
                                file_content = the_file.read()
                        # Change extension from .gz to .xml
                        file_name = os.path.splitext(file_name)[0] + ".xml"
                        extract_successfully = True
                        Logger.debug(f"Extracted zipped file to {file_name}")
                    except (
                        Exception
                    ) as extract_error:  # pylint: disable=broad-exception-caught
                        Logger.error(f"Failed to extract {file_name}: {extract_error}")
                        error = str(extract_error)
                        extract_successfully = False
            else:
                extract_successfully = True

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
    Simple in-memory queue for testing.
    Not suitable for production - data is lost on restart.

    Messages can be consumed as they arrive using the async generator
    returned by get_all_messages().
    """

    def __init__(self, queue_name: str = "default"):
        """
        Initialize in-memory queue.

        Args:
            queue_name: Name of the queue
        """
        self.queue_name = queue_name
        self._queue: asyncio.Queue = asyncio.Queue()

    async def send(self, message: Dict[str, Any]) -> None:
        """Add message to queue."""
        await self._queue.put(message)
        Logger.debug(f"Added message to in-memory queue: {message['file_name']}")

    def get_queue_name(self) -> str:
        """Return queue name."""
        return f"memory:{self.queue_name}"

    async def close(self) -> None:
        """Signal that no more messages will be sent."""
        await self._queue.put(None)

    async def get_all_messages(self):
        """
        Async generator that yields messages as they arrive.
        Stops when close() is called.
        """
        while True:
            message = await self._queue.get()
            if message is None:
                break
            yield message
