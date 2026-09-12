"""Status-contract validation: duplicate listing events are ok; two fails are not."""

import unittest
from datetime import datetime, timedelta

from il_supermarket_scarper.utils.scraping.scraper_status_contract import (
    CollectedStatus,
    DownloadedStatus,
    FailedStatus,
    FileName,
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


def _collected(**kwargs):
    return CollectedStatus(
        task_id=TASK, file_name=FILE, link_collected=LINK, **kwargs
    )


def _downloaded(extracted=True, **kwargs):
    return DownloadedStatus(
        task_id=TASK,
        file_name=FILE,
        downloaded_successfully=True,
        extracted_successfully=extracted,
        **kwargs,
    )


def _verified(**kwargs):
    return VerifiedDownload(
        task_id=TASK,
        file_name=FILE,
        system_timestamp=kwargs.pop("system_timestamp", NOW),
        listing_hash=kwargs.pop("listing_hash", "abc"),
        **kwargs,
    )


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
            global_status=[_started()],
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
                _verified(
                    content_sha256="aa",
                    save_decision="created",
                    listing_hash="hash-a",
                ),
                _verified(
                    content_sha256="bb",
                    save_decision="hash_mismatch",
                    listing_hash="hash-b",
                ),
            ],
        )
        self.assertTrue(status.validate_file_status())

    def test_duplicate_failed_is_invalid(self):
        """Two failed events for one file name are a contract break."""
        status = ScraperStatusOutput(
            global_status=[_started()],
            events=[
                _saw(),
                _collected(),
                FailedStatus(task_id=TASK, file_name=FILE, download_url=LINK),
                FailedStatus(task_id=TASK, file_name=FILE, download_url=LINK),
            ],
        )
        self.assertFalse(status.validate_file_status())

    def test_failed_same_name_different_entry_ids_is_valid(self):
        """Two fails for the same FileNm are ok when they are different stories."""
        status = ScraperStatusOutput(
            global_status=[_started()],
            events=[
                SawStatus(task_id=TASK, file_name=FILE, link=LINK, entry_id="e1"),
                CollectedStatus(
                    task_id=TASK, file_name=FILE, link_collected=LINK, entry_id="e1"
                ),
                FailedStatus(
                    task_id=TASK, file_name=FILE, download_url=LINK, entry_id="e1"
                ),
                SawStatus(task_id=TASK, file_name=FILE, link=LINK, entry_id="e2"),
                CollectedStatus(
                    task_id=TASK, file_name=FILE, link_collected=LINK, entry_id="e2"
                ),
                FailedStatus(
                    task_id=TASK, file_name=FILE, download_url=LINK, entry_id="e2"
                ),
            ],
        )
        self.assertTrue(status.validate_file_status())

    def test_duplicate_failed_same_entry_id_is_invalid(self):
        """Two fails for one entry_id are a contract break."""
        status = ScraperStatusOutput(
            global_status=[_started()],
            events=[
                SawStatus(task_id=TASK, file_name=FILE, link=LINK, entry_id="e1"),
                CollectedStatus(
                    task_id=TASK, file_name=FILE, link_collected=LINK, entry_id="e1"
                ),
                FailedStatus(
                    task_id=TASK, file_name=FILE, download_url=LINK, entry_id="e1"
                ),
                FailedStatus(
                    task_id=TASK, file_name=FILE, download_url=LINK, entry_id="e1"
                ),
            ],
        )
        self.assertFalse(status.validate_file_status())

    def test_duplicate_collected_same_entry_id_is_invalid(self):
        """entry_id stories may not repeat collected."""
        status = ScraperStatusOutput(
            global_status=[_started()],
            events=[
                _saw(entry_id="e1"),
                _collected(entry_id="e1"),
                _collected(entry_id="e1"),
                _downloaded(entry_id="e1", extracted=False),
            ],
        )
        self.assertFalse(status.validate_file_status())

    def test_successful_extract_without_verified_is_invalid(self):
        """A successful extract must also be recorded as verified."""
        status = ScraperStatusOutput(
            global_status=[_started()],
            events=[_saw(), _collected(), _downloaded(extracted=True)],
            verified_downloads=[],
        )
        self.assertFalse(status.validate_file_status())

    def test_failed_extract_without_verified_is_valid(self):
        """Failed extract can remain downloaded-only."""
        status = ScraperStatusOutput(
            global_status=[_started()],
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
                    task_id=TASK,
                    file_name=other,
                    system_timestamp=NOW,
                    listing_hash="other",
                ),
            ],
        )
        self.assertFalse(status.validate_file_status())

    def test_failed_file_needs_collected(self):
        """A failed download still needs a collected event."""
        status = ScraperStatusOutput(
            global_status=[_started()],
            events=[
                _saw(),
                FailedStatus(task_id=TASK, file_name=FILE, download_url=None),
            ],
        )
        self.assertFalse(status.validate_file_status())

    def test_events_without_started_are_invalid(self):
        """Any event journal requires a started global status."""
        status = ScraperStatusOutput(
            events=[_saw(), _collected(), _downloaded(extracted=False)],
        )
        self.assertFalse(status.validate_file_status())

    def test_mixed_entry_id_and_name_keys_are_invalid(self):
        """Same FileNm must not appear under both entry_id and name-only keys."""
        status = ScraperStatusOutput(
            global_status=[_started()],
            events=[
                _saw(entry_id="e1"),
                _collected(entry_id="e1"),
                _downloaded(entry_id="e1", extracted=False),
                _saw(),
                _collected(),
                _downloaded(extracted=False),
            ],
        )
        self.assertFalse(status.validate_file_status())

    def test_entry_id_timestamp_order_is_enforced(self):
        """Within one entry_id story, later stages cannot precede earlier ones."""
        early = NOW
        late = NOW + timedelta(minutes=1)
        status = ScraperStatusOutput(
            global_status=[_started()],
            events=[
                _saw(entry_id="e1", system_timestamp=late),
                _collected(entry_id="e1", system_timestamp=early),
                _downloaded(entry_id="e1", extracted=False, system_timestamp=late),
            ],
        )
        self.assertFalse(status.validate_file_status())

    def test_failed_download_without_error_is_invalid(self):
        """downloaded_successfully=False requires error_message."""
        status = ScraperStatusOutput(
            global_status=[_started()],
            events=[
                _saw(),
                _collected(),
                DownloadedStatus(
                    task_id=TASK,
                    file_name=FILE,
                    downloaded_successfully=False,
                    extracted_successfully=False,
                ),
            ],
        )
        self.assertFalse(status.validate_file_status())

    def test_invalid_save_decision_is_rejected(self):
        """Unknown save_decision values break the contract."""
        status = ScraperStatusOutput(
            global_status=[_started()],
            events=[
                _saw(),
                _collected(),
                _downloaded(extracted=True, save_decision="nope", content_sha256="aa"),
            ],
            verified_downloads=[_verified(content_sha256="aa", save_decision="nope")],
        )
        self.assertFalse(status.validate_file_status())

    def test_entry_id_verified_needs_digest_when_download_has_one(self):
        """Successful extract with a digest must keep that digest on verified."""
        status = ScraperStatusOutput(
            global_status=[_started()],
            events=[
                _saw(entry_id="e1"),
                _collected(entry_id="e1"),
                _downloaded(
                    entry_id="e1",
                    extracted=True,
                    content_sha256="aa",
                    save_decision="created",
                ),
            ],
            verified_downloads=[
                _verified(entry_id="e1", save_decision="created", listing_hash="h1"),
            ],
        )
        self.assertFalse(status.validate_file_status())

    def test_filename_rejects_path_separators(self):
        """FileName restores path-separator rejection."""
        with self.assertRaises(ValueError):
            FileName.validate("PromoFull7290/bad-20260907-000001")


if __name__ == "__main__":
    unittest.main()
