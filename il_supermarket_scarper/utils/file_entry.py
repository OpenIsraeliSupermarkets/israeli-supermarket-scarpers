"""Data type for file entries flowing through the scraper pipeline."""

from typing import NamedTuple, Optional


class FileEntry(NamedTuple):
    """
    Encapsulates a file entry with name, url, and size.

    Used by AsyncGenerators throughout the engine pipeline instead of raw tuples.
    Preserves tuple unpacking: name, url, size = file_entry
    """

    name: str
    url: str
    size: Optional[int]
