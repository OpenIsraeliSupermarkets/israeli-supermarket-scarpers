"""Files the caller asked to download again (``re_download``)."""

from typing import Iterable, List, Optional, Set

from .file_entry import FileEntry


class ForcedDownloads:
    """A listed file is forced when any requested entry is a substring of its name."""

    def __init__(self, names: Optional[Iterable[str]] = None):
        self.names: List[str] = list(names or [])
        self.pending: Set[str] = set(self.names)

    def matches(self, file: FileEntry) -> bool:
        """True when ``file`` was requested."""
        return any(name in file.name for name in self.names)

    def mark_listed(self, file: FileEntry) -> None:
        """Drop the entries ``file`` satisfies from ``pending``."""
        self.pending.difference_update(n for n in self.names if n in file.name)
