"""Configuration classes for scraper behavior."""

from dataclasses import dataclass, field
from typing import Optional
from il_supermarket_scarper.utils.file_output import (
    FileOutput,
    DiskFileOutput,
    QueueFileOutput,
)


@dataclass
class ScraperConfig:
    """
    Configuration for scraper behavior.

    All output configuration (disk folder, queue, etc.) is handled through
    the file_output parameter, which can be any FileOutput implementation.
    """

    # Output configuration - single unified approach
    file_output: FileOutput

    # Filtering options
    filter_null: bool = True
    filter_zero: bool = True
    min_size: int = 100  # bytes
    max_size: int = 10_000_000  # 10 MB

    # Scraping options
    suppress_exception: bool = False

    # Additional metadata to include with files
    metadata: dict = field(default_factory=dict)

    def is_disk_output(self) -> bool:
        """Check if output is to disk (vs queue)."""
        return isinstance(self.file_output, DiskFileOutput)

    def is_queue_output(self) -> bool:
        """Check if output is to a queue."""
        return isinstance(self.file_output, QueueFileOutput)

    @classmethod
    def disk(
        cls, folder_name: str, chain_name: str, extract_gz: bool = True, **kwargs
    ) -> "ScraperConfig":
        """
        Create config for disk output.

        Args:
            folder_name: Output folder path
            chain_name: Name of the chain
            extract_gz: Whether to extract .gz files
            **kwargs: Other configuration options
        """
        from il_supermarket_scarper.utils.status import get_output_folder

        storage_path = get_output_folder(chain_name, folder_name=folder_name)
        file_output = DiskFileOutput(storage_path, extract_gz=extract_gz)
        return cls(file_output=file_output, **kwargs)

    @classmethod
    def queue(cls, file_output: FileOutput, **kwargs) -> "ScraperConfig":
        """Create config for queue output."""
        return cls(file_output=file_output, **kwargs)
