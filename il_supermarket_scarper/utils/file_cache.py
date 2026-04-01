import fcntl
import hashlib
import os
import json
import time
from functools import wraps

_CACHE_DIR = ".cache"


def file_cache(ttl=None):
    """Decorator to cache function results in a file with an optional TTL (time-to-live).

    Uses per-key exclusive file locks so that only one process fetches a given
    cache entry; all others block and then read from the cache once it is ready.
    """

    def get_cache_file(func_name):
        return os.path.join(_CACHE_DIR, f"{func_name}_cache.json")

    def get_lock_file(func_name, cache_key):
        key_hash = hashlib.md5(cache_key.encode()).hexdigest()
        return os.path.join(_CACHE_DIR, f"{func_name}_{key_hash}.lock")

    def load_cache(cache_file):
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_cache(cache_file, cache_data):
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

    def _is_valid(entry):
        return ttl is None or (time.time() - entry["timestamp"]) <= ttl

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_file = get_cache_file(func.__name__)
            cache_key = generate_cache_key(args, kwargs)

            # Fast path: check without lock first
            cache = load_cache(cache_file)
            entry = cache.get(cache_key)
            if entry and _is_valid(entry):
                return entry["result"]

            # Slow path: acquire exclusive per-key lock, then re-check
            os.makedirs(_CACHE_DIR, exist_ok=True)
            lock_path = get_lock_file(func.__name__, cache_key)
            with open(lock_path, "w", encoding="utf-8") as lock_f:
                fcntl.flock(lock_f, fcntl.LOCK_EX)
                try:
                    cache = load_cache(cache_file)
                    entry = cache.get(cache_key)
                    if entry and _is_valid(entry):
                        return entry["result"]

                    result = func(*args, **kwargs)
                    cache[cache_key] = {"result": result, "timestamp": time.time()}
                    save_cache(cache_file, cache)
                    return result
                finally:
                    fcntl.flock(lock_f, fcntl.LOCK_UN)

        def generate_cache_key(args, kwargs):
            key_parts = []
            for arg in args:
                if isinstance(arg, (int, float, str, bool)):
                    key_parts.append(str(arg))
                else:
                    raise ValueError(f"Unsupported argument type: {type(arg)}")
            for k, v in kwargs.items():
                if isinstance(v, (int, float, str, bool)):
                    key_parts.append(f"{k}={v}")
                else:
                    raise ValueError(f"Unsupported keyword argument type: {type(v)}")
            return "|".join(key_parts)

        return wrapper

    return decorator
