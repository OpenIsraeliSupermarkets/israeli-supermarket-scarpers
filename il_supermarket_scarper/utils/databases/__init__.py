import os
from .base import AbstractDataBase
from .json_file import JsonDataBase
from .mongo import MongoDataBase
from ..folders_name import DumpFolderNames
from ..file_output import DiskFileOutput, QueueFileOutput, InMemoryQueueHandler


def create_status_database_for_scraper(scraper_name, config):
    """Create a status database instance for a specific scraper based on config.

    Args:
        scraper_name: Name of the scraper (e.g., "BAREKET")
        config: Configuration dictionary with database_type and other settings

    Returns:
        JsonDataBase or MongoDataBase instance
    """
    target_folder = DumpFolderNames[scraper_name].value
    database_name = target_folder

    # Use default config if None
    if config is None:
        config = {
            "database_type": "json",
            "base_path": "dumps/status",
        }

    database_type = config.get("database_type", "json")

    if database_type == "json":
        # JSON file database
        base_path = config.get("base_path", "dumps/status")
        return JsonDataBase(database_name, base_path=base_path)

    if database_type == "mongo":
        # MongoDB database
        db = MongoDataBase(database_name)
        db.create_connection()
        return db

    raise ValueError(
        f"Unknown database_type: {database_type}. Must be 'json' or 'mongo'"
    )


def create_file_output_for_scraper(scraper_name, config):
    """
    Create a file_output instance for a specific scraper based on config.

    Args:
        scraper_name: Name of the scraper
        config: Configuration dictionary
    """
    target_folder = DumpFolderNames[scraper_name].value

    # Use default config if None
    if config is None:
        config = {
            "output_mode": "disk",
            "base_storage_path": "dumps",
        }

    if config.get("output_mode") == "disk":
        # Disk output mode
        base_path = config.get("base_storage_path", "dumps")
        return DiskFileOutput(storage_path=os.path.join(base_path, target_folder))

    if config.get("output_mode") == "queue":
        # Queue output mode
        queue_type = config.get("queue_type", "memory")

        if queue_type == "memory":
            return QueueFileOutput(InMemoryQueueHandler(queue_name=target_folder))
    return None
