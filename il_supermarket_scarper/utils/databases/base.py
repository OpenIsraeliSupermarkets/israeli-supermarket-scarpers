from abc import ABC, abstractmethod


class AbstractDataBase(ABC):
    """Abstract base class for database operations."""

    def __init__(self, database_name, collection_status=False) -> None:
        self.database_name = database_name.replace(" ", "_").lower()
        self.collection_status = collection_status

    @abstractmethod
    def enable_collection_status(self):
        """Enable data collection to the database."""
        pass

    @abstractmethod
    def insert_document(self, collection_name, document):
        """Insert a document into a collection."""
        pass

    @abstractmethod
    def find_document(self, collection_name, query):
        """Find a document in a collection based on a query."""
        pass

    def is_collection_enabled(self):
        """Check if collection is enabled."""
        return self.collection_status