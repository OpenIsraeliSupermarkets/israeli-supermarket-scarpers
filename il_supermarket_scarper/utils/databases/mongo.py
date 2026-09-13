from il_supermarket_scarper.utils.scraping.status import _now
from .base import AbstractDataBase


pymongo_installed = True
try:
    import pymongo
except ImportError:
    pymongo_installed = False


class MongoDataBase(AbstractDataBase):
    """A class that represents a MongoDB database."""

    def __init__(self, database_name, connection_url, collection_name) -> None:
        super().__init__(database_name)
        self.myclient = None
        self.store_db = None
        self.connection_url = connection_url
        self.collection_name = collection_name

    def create_connection(self):
        """Create a connection to the MongoDB database."""
        if pymongo_installed:
            self.myclient = pymongo.MongoClient(
                f"{self.connection_url}/{self.collection_name}"
            )
            self.store_db = self.myclient[self.database_name]

    def _do_insert_document(self, collection_name, document):
        """Persist a single document in a MongoDB collection."""
        if self.store_db is None:
            self.create_connection()
        self.store_db[collection_name].insert_one(document)
        self._update_last_modified()

    def find_document(self, collection_name, query):
        """Return the first matching document, or None."""
        if self.store_db is None:
            self.create_connection()
        return self.store_db[collection_name].find_one(query)

    def list_documents(self, collection_name):
        """Return all documents in a collection (empty list if missing)."""
        if self.store_db is None:
            self.create_connection()
        return list(self.store_db[collection_name].find({}))

    def _update_last_modified(self):
        """Update the last modified timestamp to current time."""
        if self.store_db is None:
            self.create_connection()
        self.store_db["_metadata"].update_one(
            {}, {"$set": {"last_modified": _now()}}, upsert=True
        )

    def get_last_modified(self):
        """Get the last modified timestamp when scraper last wrote to this database."""
        if self.store_db is None:
            self.create_connection()
        metadata = self.store_db["_metadata"].find_one({})
        if metadata and "last_modified" in metadata:
            return metadata["last_modified"]
        return None
