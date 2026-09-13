from typing import Optional

from il_supermarket_scarper.utils.files.file_entry import FileEntry
from il_supermarket_scarper.utils.files.save_policy import SaveDecision


class ScrapingResult:  # pylint: disable=too-many-instance-attributes
    """
    Represents the result of a scraping operation.
    Holds metadata, status, error information, and supports len().

    Example::

        ScrapingResult(
            file_entry=FileEntry(
                name='Price7290875100001-009-202601121522',
                url='http://example.test/file',
                size=1,
            ),
            downloaded=True,
            save_decision=SaveDecision.CREATED,
            extract_succefully=True,
            content_sha256='abc',
            saved_file_name='Price7290875100001-009-202601121522.xml',
        )
    """

    def __init__(
        self,
        file_entry: FileEntry,
        downloaded: bool,
        save_decision: Optional[SaveDecision],
        extract_succefully: bool,
        content_sha256: Optional[str] = None,
        error: Optional[str] = None,
        restart_and_retry: bool = False,
        source_corrupt: bool = False,
        saved_file_name: Optional[str] = None,
    ):
        self.file_entry = file_entry
        # Prefer post-extract name so verified digests match FileOutput keys.
        self.file_name = saved_file_name or file_entry.name
        self.downloaded = downloaded
        self.save_decision = getattr(save_decision, "value", save_decision)
        self.extract_succefully = extract_succefully
        # Only set if the file was downloaded and extracted successfully
        self.content_sha256 = content_sha256
        self.error = error
        self.restart_and_retry = restart_and_retry
        # True when the remote file itself is truncated/corrupt (download size
        # matched, extract still failed after retries). Not a fetch bug.
        self.source_corrupt = source_corrupt

    def __len__(self) -> int:
        """
        Returns 1 if extraction was successful, 0 otherwise.
        This allows ScrapingResult to be used in contexts expecting a length.
        """
        return 1 if self.extract_succefully else 0

    def __repr__(self) -> str:
        """String representation of the ScrapingResult."""
        return (
            f"ScrapingResult(file_name='{self.file_name}', "
            f"downloaded={self.downloaded}, "
            f"extract_succefully={self.extract_succefully}, "
            f"error={self.error!r}, "
            f"restart_and_retry={self.restart_and_retry}, "
            f"source_corrupt={self.source_corrupt})"
        )

    def __bool__(self) -> bool:
        """Returns True if extraction was successful."""
        return self.extract_succefully
