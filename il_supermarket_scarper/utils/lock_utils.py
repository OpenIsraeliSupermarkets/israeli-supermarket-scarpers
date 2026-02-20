from threading import Lock
from functools import wraps


class LockManager:
    """Manages locks based on string values."""

    def __init__(self):
        self.locks = {}

    def get_lock(self, key):
        """Get or create a lock based on the string key."""
        if key not in self.locks:
            self.locks[key] = Lock()
        return self.locks[key]


lock_manager = LockManager()


def lock_by_string():
    """
    Decorator to apply a lock based on a string key.
    :param lock_key_func: A function that returns the string key for which the lock will be applied.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(collection_name, *args, **kwargs):
            # Get the key for which to acquire the lock (based on the arguments)
            lock = lock_manager.get_lock(collection_name)

            with lock:
                return func(collection_name, *args, **kwargs)

        return wrapper

    return decorator
