import os
from ..logger import Logger
from ..status import _now
from .base import AbstractDataBase


pymongo_installed = True
try:
    import pymongo
    from pymongo.errors import ServerSelectionTimeoutError
except ImportError:
    pymongo_installed = False


class MongoDataBase(AbstractDataBase):
    """A class that represents a MongoDB database."""

    def __init__(self, database_name) -> None:
        super().__init__(database_name)
        self.myclient = None
        self.store_db = None

    def create_connection(self):
        """Create a connection to the MongoDB database."""
        if pymongo_installed:
            url = os.environ.get("MONGO_URL", "localhost")
            port = os.environ.get("MONGO_PORT", "27017")
            self.myclient = pymongo.MongoClient(f"mongodb://{url}:{port}/")
            self.store_db = self.myclient[self.database_name]

    def insert_document(self, collection_name, document):
        """Insert a document into a MongoDB collection."""
        self.store_db[collection_name].insert_one(document)
        self._update_last_modified()

    def already_downloaded(self, collection_name, query):
        """Find a document in a MongoDB collection."""
        return self.store_db[collection_name].find_one(query)

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
