import os
import json
import tempfile
from datetime import datetime
import pytz
from il_supermarket_scarper.utils.network.lock_utils import lock_by_string
from il_supermarket_scarper.utils.core.logger import Logger
from il_supermarket_scarper.utils.scraping.status import _now
from .base import AbstractDataBase


class JsonDataBase(AbstractDataBase):
    """A class that represents a JSON-based database."""

    def __init__(self, database_name, base_path="json_db") -> None:
        super().__init__(database_name)
        self.base_path = base_path
        self.database_file = f"{self.database_name}.json"
        self._ensure_db_directory_exists()
        self._ensure_db_file_exists()

    def _ensure_db_directory_exists(self):
        """Ensure the base directory for the JSON database exists."""
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path, exist_ok=True)

    def _ensure_db_file_exists(self):
        """Ensure the database file exists."""
        file_path = self._get_database_file_path()
        if not os.path.exists(file_path):
            self._atomic_write_json(file_path, {})  # Initialize with an empty dict

    def _get_database_file_path(self):
        """Get the full path to the database JSON file."""
        return os.path.join(self.base_path, self.database_file)

    def _read_database(self):
        """Read the JSON database file and return its contents."""
        file_path = self._get_database_file_path()
        data = {}

        # Load existing data from the file
        if os.path.exists(file_path):
            corrupted = False
            with open(file_path, "r", encoding="utf-8") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    corrupted = True
            if corrupted:
                backup = self._quarantine_corrupt_file(file_path)
                Logger.error(
                    f"File {file_path} is corrupted; moved it to {backup} "
                    "and starting from an empty database."
                )
                data = {}
        return data

    @staticmethod
    def _quarantine_corrupt_file(file_path):
        """Move an unreadable database file aside so the next write cannot
        overwrite it. Returns the backup path."""
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        backup = f"{file_path}.corrupt-{stamp}"
        os.replace(file_path, backup)
        return backup

    @staticmethod
    def _atomic_write_json(file_path, data, **dump_kwargs):
        """Write ``data`` as JSON to ``file_path`` so that a reader sees either
        the old file or the new one, never a partial one.

        The JSON goes to a temp file in the same directory, then is
        ``os.replace``-d onto the target (atomic on POSIX and Windows). If
        anything fails before the replace, the temp file is removed and the
        previous file is left untouched.

        No fsync (#241): a killed process can't leave a partial file, because
        the replace happens only after the temp file is closed. fsync only
        protects against power loss, and doing it on every status write made
        prod scraping and parsing about twice as slow.
        """
        directory = os.path.dirname(os.path.abspath(file_path))
        fd, tmp_path = tempfile.mkstemp(
            dir=directory, prefix=f".{os.path.basename(file_path)}.", suffix=".tmp"
        )
        try:
            # mkstemp creates the file 0600; keep the mode a plain open() gave.
            os.chmod(tmp_path, JsonDataBase._target_mode(file_path))
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(data, file, **dump_kwargs)
            os.replace(tmp_path, file_path)
        except BaseException:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def _target_mode(file_path):
        """Mode of the existing file, else the umask default for a new one."""
        try:
            return os.stat(file_path).st_mode & 0o777
        except FileNotFoundError:
            umask = os.umask(0)
            os.umask(umask)
            return 0o666 & ~umask

    @staticmethod
    def _stamp_last_modified(data):
        """Set `_metadata.last_modified` to now, in the data about to be written."""
        data.setdefault("_metadata", {})["last_modified"] = _now().isoformat()

    def _write_database(self, data):
        """Write data to the JSON database file atomically."""
        self._atomic_write_json(
            self._get_database_file_path(),
            dict(sorted(data.items())),
            default=str,
            indent=4,
        )

    @lock_by_string()
    def _do_insert_documents(self, collection_name, documents):
        """Persist many documents in one JSON write."""
        data = self._read_database()
        if collection_name not in data:
            data[collection_name] = []
        data[collection_name].extend(documents)
        # One write per insert: the timestamp goes in with the data (#241)
        self._stamp_last_modified(data)
        self._write_database(data)

    @lock_by_string()
    def _do_insert_document(self, collection_name, document):
        """Persist a single document in the JSON database."""
        data = self._read_database()
        if collection_name not in data:
            data[collection_name] = []
        data[collection_name].append(document)
        # One write per insert: the timestamp goes in with the data (#241)
        self._stamp_last_modified(data)
        self._write_database(data)

    def find_document(self, collection_name, query):
        """Return the first matching document, or None."""
        for document in self.list_documents(collection_name):
            if all(item in document.items() for item in query.items()):
                return document
        return None

    def list_documents(self, collection_name):
        """Return all documents in a collection (empty list if missing)."""
        file_path = self._get_database_file_path()
        if not os.path.exists(file_path):
            return []
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                Logger.warning(f"File {file_path} is corrupted.")
                return []
        docs = data.get(collection_name, [])
        if not isinstance(docs, list):
            return []
        return docs

    def _update_last_modified(self):
        """Update the last modified timestamp to current time."""
        data = self._read_database()
        # Stored as an ISO format string for reliable parsing
        self._stamp_last_modified(data)
        self._write_database(data)

    def get_last_modified(self):
        """Get the last modified timestamp when scraper last wrote to this database."""
        data = self._read_database()
        if "_metadata" in data and "last_modified" in data["_metadata"]:
            # Parse the timestamp if it's a string (from JSON)
            last_modified = data["_metadata"]["last_modified"]
            if isinstance(last_modified, str):

                # Parse ISO format string
                try:
                    # Handle timezone-aware ISO strings
                    if last_modified.endswith("Z"):
                        last_modified = last_modified.replace("Z", "+00:00")
                    parsed = datetime.fromisoformat(last_modified)
                    # Ensure timezone-aware
                    if parsed.tzinfo is None:
                        parsed = pytz.timezone("Asia/Jerusalem").localize(parsed)
                    return parsed
                except (ValueError, AttributeError) as e:
                    Logger.warning(f"Failed to parse last_modified timestamp: {e}")
                    return None
            # If it's already a datetime object (shouldn't happen with JSON, but handle it)
            return last_modified
        return None
