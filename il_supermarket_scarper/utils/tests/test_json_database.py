"""Crash-safety tests for the JSON status database (issue #234)."""

import json
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

from il_supermarket_scarper.utils.databases import JsonDataBase
from il_supermarket_scarper.utils.databases import json_file

COLLECTION = "verified_downloads"


def _seed(db, rows):
    db.insert_documents(
        COLLECTION, [{"file_name": f"f{i}.gz", "sha256": "x" * 64} for i in range(rows)]
    )


def _read_bytes(path):
    with open(path, "rb") as file:
        return file.read()


def _leftovers(directory):
    return [n for n in os.listdir(directory) if n.endswith(".tmp")]


class TestJsonDataBaseAtomicWrite(unittest.TestCase):
    """A failed or interrupted write must never lose the previous file."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.base = self._tmp.name
        self.db = JsonDataBase("chain", self.base)
        self.path = os.path.join(self.base, "chain.json")

    def tearDown(self):
        self._tmp.cleanup()

    def test_dump_failing_midway_keeps_previous_file(self):
        """json.dump raising after partial output leaves the old rows readable."""
        _seed(self.db, 50)
        before = _read_bytes(self.path)

        def partial_dump(_obj, fp, **_kwargs):
            fp.write('{"verified_downloads": [{"file_name": "f0')
            raise OSError("disk full")

        with mock.patch.object(json_file.json, "dump", side_effect=partial_dump):
            with self.assertRaises(OSError):
                self.db.insert_document(COLLECTION, {"file_name": "new.gz"})

        self.assertEqual(_read_bytes(self.path), before)
        fresh = JsonDataBase("chain", self.base)
        self.assertEqual(len(fresh.list_documents(COLLECTION)), 50)
        self.assertEqual(_leftovers(self.base), [])

    def test_replace_failing_keeps_previous_file_and_cleans_temp(self):
        """A failure at the rename step also leaves no temp file behind."""
        _seed(self.db, 5)
        with mock.patch.object(json_file.os, "replace", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                self.db.insert_document(COLLECTION, {"file_name": "new.gz"})
        self.assertEqual(len(self.db.list_documents(COLLECTION)), 5)
        self.assertEqual(_leftovers(self.base), [])

    def test_format_unchanged(self):
        """The file stays plain indented JSON that json.load reads."""
        _seed(self.db, 2)
        with open(self.path, encoding="utf-8") as file:
            text = file.read()
        data = json.loads(text)
        self.assertEqual(len(data[COLLECTION]), 2)
        self.assertIn("last_modified", data["_metadata"])
        self.assertIn('\n    "', text)  # indent=4 kept

    @unittest.skipIf(os.name == "nt", "POSIX file modes")
    def test_file_mode_kept(self):
        """The rewrite keeps the file's permissions (mkstemp would make 0600)."""
        os.chmod(self.path, 0o644)
        _seed(self.db, 1)
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o644)

    def test_corrupt_file_is_moved_aside_not_overwritten(self):
        """A file left cut off by an older version is kept for recovery."""
        _seed(self.db, 20)
        with open(self.path, "rb") as file:
            truncated = file.read()[:-40]
        with open(self.path, "wb") as file:
            file.write(truncated)

        self.db.insert_document(COLLECTION, {"file_name": "new.gz"})

        backups = [n for n in os.listdir(self.base) if ".corrupt-" in n]
        self.assertEqual(len(backups), 1)
        with open(os.path.join(self.base, backups[0]), "rb") as file:
            self.assertEqual(file.read(), truncated)
        self.assertEqual(len(self.db.list_documents(COLLECTION)), 1)


@unittest.skipUnless(hasattr(signal, "SIGKILL"), "needs SIGKILL")
class TestJsonDataBaseSigkill(unittest.TestCase):
    """The reproduction from issue #234: SIGKILL a writer mid-loop."""

    def test_sigkill_during_writes_never_loses_rows(self):
        """After repeated kills the file is valid JSON with all seeded rows."""
        with tempfile.TemporaryDirectory() as base:
            seed_rows = 5000
            _seed(JsonDataBase("chain", base), seed_rows)
            writer = textwrap.dedent(f"""
                from il_supermarket_scarper.utils.databases import JsonDataBase
                db = JsonDataBase("chain", {base!r})
                i = 0
                while True:
                    db.insert_document({COLLECTION!r}, {{"file_name": f"n{{i}}.gz"}})
                    i += 1
                """)
            path = os.path.join(base, "chain.json")
            for _ in range(3):
                with subprocess.Popen([sys.executable, "-c", writer]) as proc:
                    time.sleep(1.5)
                    proc.send_signal(signal.SIGKILL)
                    proc.wait()
                with open(path, encoding="utf-8") as file:
                    rows = json.load(file)[COLLECTION]
                self.assertGreaterEqual(len(rows), seed_rows)
            self.assertEqual([n for n in os.listdir(base) if ".corrupt-" in n], [])


if __name__ == "__main__":
    unittest.main()
