import os
import json
from il_supermarket_scarper.utils import Logger
from .base import AbstractDataBase


class JsonDataBase(AbstractDataBase):
    """A class that represents a JSON-based database."""

    def __init__(self, database_name, base_path="json_db") -> None:
        super().__init__(database_name, collection_status=True)
        self.base_path = base_path
        self._ensure_db_directory_exists()

    def _ensure_db_directory_exists(self):
        """Ensure the base directory for the JSON database exists."""
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    def _get_collection_file_path(self, collection_name):
        """Get the file path for the collection (JSON file)."""
        return os.path.join(
            self.base_path, f"{self.database_name}_{collection_name}.json"
        )

    def insert_document(self, collection_name, document):
        """Insert a document into a JSON collection (file)."""
        if self.collection_status:
            file_path = self._get_collection_file_path(collection_name)
            data = []

            # Load existing data from the file if it exists
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as file:
                    try:
                        data = json.load(file)
                    except json.JSONDecodeError:
                        Logger.warning(
                            f"File {file_path} is empty or corrupted, resetting it."
                        )

            # Add the new document and save it back to the file
            data.append(document)
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, default=str, indent=4)

    def find_document(self, collection_name, query):
        """Find a document in a JSON collection (file) based on a query."""
        if self.collection_status:
            file_path = self._get_collection_file_path(collection_name)

            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as file:
                    try:
                        data = json.load(file)
                        # Filter the documents based on the query
                        for document in data:
                            if all(item in document.items() for item in query.items()):
                                return document
                    except json.JSONDecodeError:
                        Logger.warning(f"File {file_path} is empty or corrupted.")

        return None
