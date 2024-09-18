import os
from ..logger import Logger
from .base import AbstractDataBase


PYMONGO_INSTALLED = True
try:
    import pymongo
    from pymongo.errors import ServerSelectionTimeoutError
except ImportError:
    PYMONGO_INSTALLED = False


class MongoDataBase(AbstractDataBase):
    """A class that represents a MongoDB database."""

    def __init__(self, database_name) -> None:
        super().__init__(database_name)
        self.myclient = None
        self.store_db = None

    def create_connection(self):
        """Create a connection to the MongoDB database."""
        if PYMONGO_INSTALLED:
            url = os.environ.get("MONGO_URL", "localhost")
            port = os.environ.get("MONGO_PORT", "27017")
            self.myclient = pymongo.MongoClient(f"mongodb://{url}:{port}/")
            self.store_db = self.myclient[self.database_name]

    def enable_collection_status(self):
        """Enable data collection to MongoDB."""
        if PYMONGO_INSTALLED:
            self.set_collection_status(True)
            self.create_connection()
        else:
            Logger.info("Can't enable collection. Please install pymongo.")

    def insert_document(self, collection_name, document):
        """Insert a document into a MongoDB collection."""
        if self.is_collection_enabled():
            try:
                self.store_db[collection_name].insert_one(document)
            except ServerSelectionTimeoutError:
                self.set_collection_status(False)
                Logger.error(
                    "Failed to connect to MongoDB. Collection status disabled."
                )

    def find_document(self, collection_name, query):
        """Find a document in a MongoDB collection."""
        if self.is_collection_enabled():
            return self.store_db[collection_name].find_one(query)
        return None
