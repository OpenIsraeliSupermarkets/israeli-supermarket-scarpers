import os
from ..logger import Logger
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

    def find_document(self, collection_name, query):
        """Find a document in a MongoDB collection."""
        return self.store_db[collection_name].find_one(query)
