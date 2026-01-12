
from typing import Optional


class ScrapingResult:
    """
    Represents the result of a scraping operation.
    Holds metadata, status, error information, and supports len().
    Example:
        ScrapingResult(
            file_name='Price7290875100001-009-202601121522',
            downloaded=True,
            extract_succefully=True,
            error=None,
            restart_and_retry=False,
        )
    """

    def __init__(
        self,
        file_name: str,
        downloaded: bool,
        extract_succefully: bool,
        error: Optional[str] = None,
        restart_and_retry: bool = False,
    ):
        self.file_name = file_name
        self.downloaded = downloaded
        self.extract_succefully = extract_succefully
        self.error = error
        self.restart_and_retry = restart_and_retry

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
            f"restart_and_retry={self.restart_and_retry})"
        )

    def __bool__(self) -> bool:
        """Returns True if extraction was successful."""
        return self.extract_succefully
