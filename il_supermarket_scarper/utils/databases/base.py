from abc import ABC, abstractmethod


class AbstractDataBase(ABC):
    """Abstract base class for database CRUD operations."""

    def __init__(self, database_name) -> None:
        self.database_name = database_name.replace(" ", "_").lower()

    def get_database_name(self):
        """Get the name of the database."""
        return self.database_name

    def insert_document(self, collection_name, document):
        """Insert a single document."""
        self._do_insert_document(collection_name, document)

    def insert_documents(self, collection_name, documents):
        """Insert many documents."""
        self._do_insert_documents(collection_name, documents)

    @abstractmethod
    def _do_insert_document(self, collection_name, document):
        """Persist a single document."""

    def _do_insert_documents(self, collection_name, documents):
        """Persist many documents (default: one-by-one)."""
        for document in documents:
            self._do_insert_document(collection_name, document)

    def find_document(self, collection_name, query):  # pylint: disable=unused-argument
        """Return the first matching document, or None."""
        return None

    def list_documents(self, collection_name):  # pylint: disable=unused-argument
        """Return all documents in a collection (empty list if missing)."""
        return []

    @abstractmethod
    def get_last_modified(self):
        """Get the last modified timestamp when scraper last wrote to this database."""

    @abstractmethod
    def _update_last_modified(self):
        """Update the last modified timestamp to current time."""
