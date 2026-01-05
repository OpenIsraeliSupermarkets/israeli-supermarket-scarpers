"""Abstract file output interface for saving scraped files."""

from abc import ABC, abstractmethod
from typing import Any, Dict
import os
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
        pass

    @abstractmethod
    def make_sure_accassible(self):
        """create the storage path"""
        pass

    @abstractmethod
    def get_output_location(self) -> str:
        """Get a string representation of where files are being saved."""
        pass

    @abstractmethod
    def get_storage_path(self) -> str:
        """Get the file system path for storing status files and metadata."""
        pass


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
        import asyncio

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
    """Send files to an abstract queue (for Kafka, RabbitMQ, etc.)."""

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
        """Send file to queue."""
        saved = False
        error = None

        try:
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
            "extract_successfully": saved,  # No extraction needed for queue
            "error": error,
            "metadata": metadata or {},
        }

    def get_output_location(self) -> str:
        """Return the queue location."""
        return f"queue:{self.queue_handler.get_queue_name()}"

    def get_storage_path(self) -> str:
        """Return the storage path for status files and metadata."""
        return self.storage_path


class AbstractQueueHandler(ABC):
    """Abstract base class for queue handlers (Kafka, RabbitMQ, etc.)."""

    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> None:
        """
        Send a message to the queue.

        Args:
            message: Dictionary containing file_name, file_link, file_content, metadata
        """
        pass

    @abstractmethod
    def get_queue_name(self) -> str:
        """Return the name/identifier of the queue."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the queue connection."""
        pass


class KafkaQueueHandler(AbstractQueueHandler):
    """Example Kafka queue handler implementation."""

    def __init__(self, bootstrap_servers: str, topic: str):
        """
        Initialize Kafka handler.

        Args:
            bootstrap_servers: Kafka bootstrap servers (e.g., 'localhost:9092')
            topic: Kafka topic name
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None
        Logger.info(
            f"Initialized Kafka handler for {bootstrap_servers}, topic: {topic}"
        )

    async def send(self, message: Dict[str, Any]) -> None:
        """Send message to Kafka topic."""
        # Lazy initialization of producer
        if self.producer is None:
            try:
                # Try to import aiokafka
                from aiokafka import AIOKafkaProducer
                import json

                self.producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(
                        {
                            "file_name": v["file_name"],
                            "file_link": v["file_link"],
                            "file_size": len(v["file_content"]),
                            "metadata": v["metadata"],
                        }
                    ).encode("utf-8"),
                )
                await self.producer.start()
            except ImportError:
                raise ImportError(
                    "aiokafka is not installed. Install it with: pip install aiokafka"
                )

        # For now, we send metadata only (not the full file content to avoid huge messages)
        # In production, you might want to:
        # 1. Upload file content to S3/GCS and send the URL
        # 2. Split large files into chunks
        # 3. Use a different serialization method
        await self.producer.send_and_wait(
            self.topic,
            {
                "file_name": message["file_name"],
                "file_link": message["file_link"],
                "file_content": message["file_content"],  # Warning: might be too large
                "metadata": message["metadata"],
            },
        )

    def get_queue_name(self) -> str:
        """Return Kafka topic name."""
        return f"kafka://{self.bootstrap_servers}/{self.topic}"

    async def close(self) -> None:
        """Close Kafka producer."""
        if self.producer:
            await self.producer.stop()


class InMemoryQueueHandler(AbstractQueueHandler):
    """
    Simple in-memory queue for testing.
    Not suitable for production - data is lost on restart.
    """

    def __init__(self, queue_name: str = "default"):
        """Initialize in-memory queue."""
        import asyncio

        self.queue_name = queue_name
        self.queue = asyncio.Queue()
        self.messages = []  # For debugging/testing

    async def send(self, message: Dict[str, Any]) -> None:
        """Add message to in-memory queue."""
        await self.queue.put(message)
        self.messages.append(message)
        Logger.debug(f"Added message to in-memory queue: {message['file_name']}")

    def get_queue_name(self) -> str:
        """Return queue name."""
        return f"memory:{self.queue_name}"

    async def close(self) -> None:
        """Close queue (no-op for in-memory)."""
        pass

    def get_all_messages(self):
        """Get all messages (for testing)."""
        return self.messages
