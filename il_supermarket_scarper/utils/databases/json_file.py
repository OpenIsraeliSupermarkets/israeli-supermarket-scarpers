import os
import json
from ..logger import Logger
from ..status import _now
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
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump({}, file)  # Initialize with an empty dict

    def _get_database_file_path(self):
        """Get the full path to the database JSON file."""
        return os.path.join(self.base_path, self.database_file)

    def _read_database(self):
        """Read the JSON database file and return its contents."""
        file_path = self._get_database_file_path()
        data = {}

        # Load existing data from the file
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    Logger.warning(f"File {file_path} is corrupted, resetting it.")
                    data = {}
        return data

    def _write_database(self, data):
        """Write data to the JSON database file."""
        file_path = self._get_database_file_path()

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(dict(sorted(data.items())), file, default=str, indent=4)

    def insert_documents(self, collection_name, document):
        """Insert a document into a collection inside the JSON database."""

        data = self._read_database()
        # Ensure the collection exists in the database
        if collection_name not in data:
            data[collection_name] = []

        # Add the new document to the collection
        data[collection_name].extend(document)

        # Save the updated data back to the file
        self._write_database(data)
        self._update_last_modified()

    def insert_document(self, collection_name, document):
        """Insert a document into a collection inside the JSON database."""
        data = self._read_database()
        # Ensure the collection exists in the database
        if collection_name not in data:
            data[collection_name] = []

        # Add the new document to the collection
        data[collection_name].append(document)

        # Save the updated data back to the file
        self._write_database(data)
        self._update_last_modified()

    def already_downloaded(self, collection_name, query):
        """Find a document in a collection based on a query."""
        file_path = self._get_database_file_path()

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                try:
                    data = json.load(file)

                    # Check if the collection exists
                    if collection_name in data:
                        # Filter the documents in the collection based on the query
                        for document in data[collection_name]:
                            if all(item in document.items() for item in query.items()):
                                return True
                except json.JSONDecodeError:
                    Logger.warning(f"File {file_path} is corrupted.")
        return False

    def _update_last_modified(self):
        """Update the last modified timestamp to current time."""
        data = self._read_database()
        if "_metadata" not in data:
            data["_metadata"] = {}
        # Store as ISO format string for reliable parsing
        now = _now()
        data["_metadata"]["last_modified"] = now.isoformat()
        self._write_database(data)

    def get_last_modified(self):
        """Get the last modified timestamp when scraper last wrote to this database."""
        data = self._read_database()
        if "_metadata" in data and "last_modified" in data["_metadata"]:
            # Parse the timestamp if it's a string (from JSON)
            last_modified = data["_metadata"]["last_modified"]
            if isinstance(last_modified, str):
                from datetime import datetime
                import pytz

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
