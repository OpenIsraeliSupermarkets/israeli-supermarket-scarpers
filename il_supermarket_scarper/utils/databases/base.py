from abc import ABC, abstractmethod


class AbstractDataBase(ABC):
    """Abstract base class for database operations."""

    def __init__(self, database_name, collection_status=False) -> None:
        self.database_name = database_name.replace(" ", "_").lower()
        self.collection_status = collection_status

    def enable_collection_status(self):
        """Enable data collection to the database."""
        self.collection_status = True

    @abstractmethod
    def insert_document(self, collection_name, document):
        """Insert a document into a collection."""

    @abstractmethod
    def find_document(self, collection_name, query):
        """Find a document in a collection based on a query."""

    def is_collection_enabled(self):
        """Check if collection is enabled."""
        return self.collection_status

    def set_collection_status(self, status):
        """Enable data collection to JSON storage."""
        self.collection_status = status
