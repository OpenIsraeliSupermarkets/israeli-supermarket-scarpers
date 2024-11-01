import os
import json
import time
from functools import wraps


def file_cache(ttl=None):
    """Decorator to cache function results in a file with an optional TTL (time-to-live)"""

    def get_cache_file(func_name):
        """Generate a cache file path based on the function name"""
        cache_dir = ".cache"
        return os.path.join(cache_dir, f"{func_name}_cache.json")

    def load_cache(cache_file):
        """Load the cache from the specified cache file if it exists"""
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_cache(cache_file, cache_data):
        """Save the cache to the specified cache file"""
        if not os.path.exists(".cache"):
            os.makedirs(".cache")
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache file path based on the function name
            cache_file = get_cache_file(func.__name__)

            # Load the cache from the file
            cache = load_cache(cache_file)

            # Generate a cache key from function arguments
            cache_key = generate_cache_key(args, kwargs)

            # Check if result is cached and valid
            if cache_key in cache:
                entry = cache[cache_key]
                timestamp = entry["timestamp"]

                # If ttl is set, check if cache has expired
                if ttl is not None and (time.time() - timestamp) > ttl:
                    # Cache expired, remove the entry
                    del cache[cache_key]
                else:
                    # Cache is valid, return cached result
                    return entry["result"]

            # If not cached or expired, call the function and store the result
            result = func(*args, **kwargs)

            # Save the result with the current timestamp in the cache
            cache[cache_key] = {
                "result": result,
                "timestamp": time.time(),  # Save the current time
            }
            save_cache(cache_file, cache)

            return result

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
