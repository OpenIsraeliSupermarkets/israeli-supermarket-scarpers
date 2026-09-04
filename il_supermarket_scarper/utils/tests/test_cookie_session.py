"""Tests for cookie pickle load/save under concurrent listing requests."""

import os
import pickle
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

from il_supermarket_scarper.utils.connection import session_with_cookies
from il_supermarket_scarper.utils.lock_utils import LockManager


class TestCookieSession(unittest.TestCase):
    """Concurrent cookie file access must not corrupt the pickle."""

    def test_get_lock_is_shared_under_concurrency(self):
        """First-time lock creation must return one lock for the same key."""
        manager = LockManager()
        found = []
        start = threading.Barrier(16)

        def worker():
            start.wait()
            found.append(manager.get_lock("same-key"))

        threads = [threading.Thread(target=worker) for _ in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(len({id(lock) for lock in found}), 1)

    def test_concurrent_cookie_save_does_not_corrupt_file(self):
        """Parallel session_with_cookies calls must read/write one valid pickle."""
        with tempfile.TemporaryDirectory() as tmp:
            cookie_path = os.path.join(tmp, "chain_cookies.txt")
            errors = []

            response = MagicMock()
            response.status_code = 200
            response.text = "ok"

            def run_request():
                try:
                    session_with_cookies(
                        "http://example.test/listing",
                        chain_cookie_name=cookie_path,
                    )
                except Exception as error:  # pylint: disable=broad-exception-caught
                    errors.append(error)

            session = MagicMock()
            session.get.return_value = response
            session.post.return_value = response
            session.cookies.get_dict.return_value = {"sid": "1"}

            with patch(
                "il_supermarket_scarper.utils.connection.requests.Session",
                return_value=session,
            ):
                threads = [
                    threading.Thread(target=run_request) for _ in range(8)
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()

            self.assertEqual(errors, [])
            self.assertTrue(os.path.exists(cookie_path))
            with open(cookie_path, "rb") as cookie_file:
                self.assertEqual(pickle.load(cookie_file), {"sid": "1"})
