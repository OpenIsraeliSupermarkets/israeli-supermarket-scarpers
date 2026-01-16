from abc import ABC, abstractmethod


class AbstractDataBase(ABC):
    """Abstract base class for database operations."""

    def __init__(self, database_name) -> None:
        self.database_name = database_name.replace(" ", "_").lower()

    def get_database_name(self):
        """Get the name of the database."""
        return self.database_name

    @abstractmethod
    def insert_document(self, collection_name, document):
        """Insert a document into a collection."""

    @abstractmethod
    def already_downloaded(self, collection_name, query):
        """Check if a document is already downloaded based on a query."""
        pass

    @abstractmethod
    def get_last_modified(self):
        """Get the last modified timestamp when scraper last wrote to this database."""
        pass

    @abstractmethod
    def _update_last_modified(self):
        """Update the last modified timestamp to current time."""
        pass
