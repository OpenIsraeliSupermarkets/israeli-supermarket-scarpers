"""Status-contract validation: duplicate listing events are ok; two fails are not."""

import unittest
from datetime import datetime

from il_supermarket_scarper.utils.scraper_status_contract import (
    CollectedStatus,
    DownloadedStatus,
    FailedStatus,
    SawStatus,
    ScraperStatusOutput,
    StartedStatus,
    VerifiedDownload,
)

FILE = "PromoFull7290058156016-019-502-20260907-054854"
TASK = "task-1"
NOW = datetime(2026, 9, 7, 12, 0, 0)
LINK = "http://supersapir.binaprojects.com/Download.aspx?FileNm=" + FILE


def _saw(**kwargs):
    return SawStatus(task_id=TASK, file_name=FILE, link=LINK, **kwargs)


def _collected():
    return CollectedStatus(task_id=TASK, file_name=FILE, link_collected=LINK)


def _downloaded(extracted=True, **kwargs):
    return DownloadedStatus(
        task_id=TASK,
        file_name=FILE,
        downloaded_successfully=True,
        extracted_successfully=extracted,
        **kwargs,
    )


def _verified():
    return VerifiedDownload(task_id=TASK, file_name=FILE, system_timestamp=NOW)


def _started(limit=None):
    return StartedStatus(task_id=TASK, limit=limit)


class TestScraperStatusContract(unittest.TestCase):
    """validate_file_status extra rules."""

    def test_duplicate_saw_of_same_dump_is_valid(self):
        """SuperSapir lists the same FileNm twice; one download is still valid."""
        status = ScraperStatusOutput(
            global_status=[_started(limit=1)],
            events=[_saw(), _saw(), _collected(), _downloaded()],
            verified_downloads=[_verified()],
        )
        self.assertTrue(status.validate_file_status())

    def test_duplicate_download_of_same_listing_is_valid(self):
        """Same FileNm downloaded twice (same or different hash) is valid."""
        status = ScraperStatusOutput(
            events=[
                _saw(),
                _saw(),
                _collected(),
                _collected(),
                _downloaded(
                    content_sha256="aa",
                    save_decision="created",
                ),
                _downloaded(
                    content_sha256="bb",
                    save_decision="hash_mismatch",
                ),
            ],
            verified_downloads=[
                VerifiedDownload(
                    task_id=TASK,
                    file_name=FILE,
                    system_timestamp=NOW,
                    content_sha256="aa",
                    save_decision="created",
                ),
                VerifiedDownload(
                    task_id=TASK,
                    file_name=FILE,
                    system_timestamp=NOW,
                    content_sha256="bb",
                    save_decision="hash_mismatch",
                ),
            ],
        )
        self.assertTrue(status.validate_file_status())

    def test_duplicate_failed_is_invalid(self):
        """Two failed events for one file name are a contract break."""
        status = ScraperStatusOutput(
            events=[
                _saw(),
                _collected(),
                FailedStatus(task_id=TASK, file_name=FILE, download_url=LINK),
                FailedStatus(task_id=TASK, file_name=FILE, download_url=LINK),
            ],
        )
        self.assertFalse(status.validate_file_status())

    def test_successful_extract_without_verified_is_invalid(self):
        """A successful extract must also be recorded as verified."""
        status = ScraperStatusOutput(
            events=[_saw(), _collected(), _downloaded(extracted=True)],
            verified_downloads=[],
        )
        self.assertFalse(status.validate_file_status())

    def test_failed_extract_without_verified_is_valid(self):
        """Failed extract can remain downloaded-only."""
        status = ScraperStatusOutput(
            events=[_saw(), _collected(), _downloaded(extracted=False)],
        )
        self.assertTrue(status.validate_file_status())

    def test_limit_not_exceeded(self):
        """Started limit must not be exceeded by downloaded files."""
        other = "PromoFull7290058156016-024-399-20260907-000001"
        status = ScraperStatusOutput(
            global_status=[_started(limit=1)],
            events=[
                _saw(),
                _collected(),
                _downloaded(),
                SawStatus(task_id=TASK, file_name=other, link=LINK),
                CollectedStatus(task_id=TASK, file_name=other, link_collected=LINK),
                DownloadedStatus(
                    task_id=TASK,
                    file_name=other,
                    downloaded_successfully=True,
                    extracted_successfully=True,
                ),
            ],
            verified_downloads=[
                _verified(),
                VerifiedDownload(
                    task_id=TASK, file_name=other, system_timestamp=NOW
                ),
            ],
        )
        self.assertFalse(status.validate_file_status())

    def test_failed_file_needs_collected(self):
        """A failed download still needs a collected event."""
        status = ScraperStatusOutput(
            events=[
                _saw(),
                FailedStatus(task_id=TASK, file_name=FILE, download_url=None),
            ],
        )
        self.assertFalse(status.validate_file_status())
