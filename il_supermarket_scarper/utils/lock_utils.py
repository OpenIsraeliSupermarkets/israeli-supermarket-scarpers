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
        def wrapper(scraper_status, *args, **kwargs):
            # Get the key for which to acquire the lock (based on the arguments)
            lock_key = scraper_status.chain.value
            lock = lock_manager.get_lock(lock_key)

            with lock:
                return func(scraper_status, *args, **kwargs)

        return wrapper

    return decorator
