import time


def cache_lookup(cache, key):
    """Expire cached entries using their TTL deadline."""
    value, expires = cache.get(key, (None, 0))
    return value if expires > time.time() else None


def invalidate_cache(cache, prefix):
    for key in list(cache):
        if key.startswith(prefix):
            del cache[key]
