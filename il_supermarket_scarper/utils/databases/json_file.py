import os
import json
from ..logger import Logger
from .base import AbstractDataBase


class JsonDataBase(AbstractDataBase):
    """A class that represents a JSON-based database."""

    def __init__(self, database_name, base_path="json_db") -> None:
        super().__init__(database_name, collection_status=True)
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

    def insert_document(self, collection_name, document):
        """Insert a document into a collection inside the JSON database."""
        if self.collection_status:
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

            # Ensure the collection exists in the database
            if collection_name not in data:
                data[collection_name] = []

            # Add the new document to the collection
            data[collection_name].append(document)

            # Save the updated data back to the file
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(dict(sorted(data.items())), file, default=str, indent=4)

    def find_document(self, collection_name, query):
        """Find a document in a collection based on a query."""
        if self.collection_status:
            file_path = self._get_database_file_path()

            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as file:
                    try:
                        data = json.load(file)

                        # Check if the collection exists
                        if collection_name in data:
                            # Filter the documents in the collection based on the query
                            for document in data[collection_name]:
                                if all(
                                    item in document.items() for item in query.items()
                                ):
                                    return document
                    except json.JSONDecodeError:
                        Logger.warning(f"File {file_path} is corrupted.")

        return None
