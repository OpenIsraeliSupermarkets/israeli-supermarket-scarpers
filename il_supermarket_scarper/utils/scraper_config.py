"""Configuration classes for scraper behavior."""

from dataclasses import dataclass, field
from typing import Optional
from il_supermarket_scarper.utils.file_output import (
    FileOutput,
    DiskFileOutput,
    QueueFileOutput,
)


@dataclass
class ScraperConfig:  # pylint: disable=too-many-instance-attributes
    """
    Configuration for scraper behavior.

    All output configuration (disk folder, queue, etc.) is handled through
    the file_output parameter, which can be any FileOutput implementation.
    """

    # Output configuration - single unified approach
    file_output: Optional[FileOutput] = None
    folder_name: Optional[str] = None

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
        return self.folder_name is not None or isinstance(self.file_output, DiskFileOutput)

    def is_queue_output(self) -> bool:
        """Check if output is to a queue."""
        return isinstance(self.file_output, QueueFileOutput)

    def get_file_output(self, chain_name: str, default_folder: str = None) -> FileOutput:
        """
        Get the file output handler for this config.

        Args:
            chain_name: Name of the chain (used for disk output path)
            default_folder: Default folder name if folder_name is None

        Returns:
            FileOutput instance
        """
        if self.file_output is not None:
            return self.file_output

        # Create disk output based on folder_name
        # pylint: disable=import-outside-toplevel
        from il_supermarket_scarper.utils.status import get_output_folder

        folder = self.folder_name or default_folder
        if folder is None:
            raise ValueError("Either file_output or folder_name must be provided")

        storage_path = get_output_folder(chain_name, folder_name=folder)
        return DiskFileOutput(storage_path, extract_gz=True)

    def get_folder_name(self) -> Optional[str]:
        """Get the folder name if using disk output."""
        return self.folder_name

    @classmethod
    def disk(
        cls, folder_name: str, chain_name: str = None, extract_gz: bool = True, **kwargs
    ) -> "ScraperConfig":
        """
        Create config for disk output.

        Args:
            folder_name: Output folder path
            chain_name: Name of the chain (optional, can be provided later)
            extract_gz: Whether to extract .gz files
            **kwargs: Other configuration options
        """
        if chain_name is not None:
            # pylint: disable=import-outside-toplevel
            from il_supermarket_scarper.utils.status import get_output_folder

            storage_path = get_output_folder(chain_name, folder_name=folder_name)
            file_output = DiskFileOutput(storage_path, extract_gz=extract_gz)
            return cls(file_output=file_output, folder_name=folder_name, **kwargs)

        # Just store folder_name, file_output will be created on demand
        return cls(folder_name=folder_name, **kwargs)

    @classmethod
    def queue(cls, file_output: FileOutput, **kwargs) -> "ScraperConfig":
        """Create config for queue output."""
        return cls(file_output=file_output, **kwargs)
