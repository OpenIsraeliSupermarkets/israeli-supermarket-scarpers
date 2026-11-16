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
            writer = textwrap.dedent(
                f"""
                from il_supermarket_scarper.utils.databases import JsonDataBase
                db = JsonDataBase("chain", {base!r})
                i = 0
                while True:
                    db.insert_document({COLLECTION!r}, {{"file_name": f"n{{i}}.gz"}})
                    i += 1
                """
            )
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


class TestOrphanedTempFiles(unittest.TestCase):
    """Temp files left by a killed write are cleaned up (issue #238)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.base = self._tmp.name
        self.db = JsonDataBase("bareket", self.base)
        _seed(self.db, 3)
        self.db_path = os.path.join(self.base, "bareket.json")
        self.before = _read_bytes(self.db_path)

    def tearDown(self):
        self._tmp.cleanup()

    def _touch(self, name, age_seconds=0):
        path = os.path.join(self.base, name)
        with open(path, "w", encoding="utf-8") as file:
            file.write('{"partial": ')
        stamp = time.time() - age_seconds
        os.utime(path, (stamp, stamp))
        return path

    def test_removes_orphan_and_keeps_database(self):
        """An orphan of this DB is removed; the DB file is left byte-for-byte."""
        orphan = self._touch(".bareket.json.knmujupm.tmp")
        removed = self.db.remove_orphaned_temp_files()
        self.assertEqual(removed, [orphan])
        self.assertEqual(_leftovers(self.base), [])
        self.assertEqual(_read_bytes(self.db_path), self.before)

    def test_leaves_unrelated_files(self):
        """Other databases' temp files and other files are never touched."""
        names = [
            ".shufersal.json.abcd.tmp",
            "bareket.json.tmp",
            ".bareket.json.corrupt-20261116",
            "notes.tmp",
        ]
        for name in names:
            self._touch(name, age_seconds=3600)
        self.assertEqual(self.db.remove_orphaned_temp_files(), [])
        for name in names:
            self.assertTrue(os.path.exists(os.path.join(self.base, name)), name)

    def test_open_removes_old_orphan_but_keeps_fresh_temp(self):
        """On open, only temp files past the safety margin are removed."""
        old = self._touch(".bareket.json.old1.tmp", age_seconds=3600)
        fresh = self._touch(".bareket.json.new1.tmp", age_seconds=0)
        JsonDataBase("bareket", self.base)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(fresh))
        self.assertEqual(_read_bytes(self.db_path), self.before)

    @unittest.skipUnless(hasattr(signal, "SIGKILL"), "needs SIGKILL")
    def test_sigkill_mid_write_orphan_is_removed_on_next_open(self):
        """End to end: a write killed before os.replace leaves an orphan that
        the next open removes (once past the margin); no rows are lost."""
        script = textwrap.dedent(
            f"""
            import os, signal
            from il_supermarket_scarper.utils.databases import json_file
            def die(*_a, **_k):
                os.kill(os.getpid(), signal.SIGKILL)
            json_file.os.replace = die
            db = json_file.JsonDataBase("bareket", {self.base!r})
            db.insert_document("{COLLECTION}", {{"file_name": "new.gz"}})
            """
        )
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=os.getcwd(),
            env={**os.environ, "PYTHONPATH": os.getcwd()},
            check=False,
        )
        self.assertEqual(proc.returncode, -signal.SIGKILL)
        orphans = _leftovers(self.base)
        self.assertEqual(len(orphans), 1)
        self.assertEqual(_read_bytes(self.db_path), self.before)

        with mock.patch.object(JsonDataBase, "ORPHAN_TEMP_MIN_AGE_SECONDS", 0):
            db = JsonDataBase("bareket", self.base)
        self.assertEqual(_leftovers(self.base), [])
        self.assertEqual(len(db.list_documents(COLLECTION)), 3)


if __name__ == "__main__":
    unittest.main()
