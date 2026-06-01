"""
Caching layer for database queries and API responses.
Supports Redis (production) and in-memory cache (development).
"""

import json
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import redis
from redis.exceptions import ConnectionError
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CacheBackend(ABC):
    """Abstract cache backend."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: str, expire: int = 3600) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
    
    @abstractmethod
    def flush_all(self) -> bool:
        """Flush all cache."""
        pass


class RedisCache(CacheBackend):
    """Redis-based cache backend (production)."""
    
    def __init__(self, url: str = "redis://localhost:6379/0"):
        """Initialize Redis cache."""
        try:
            self.client = redis.from_url(url, decode_responses=True)
            # Test connection
            self.client.ping()
            self.available = True
            logger.info("redis_cache_connected")
        except (ConnectionError, Exception) as e:
            logger.warning("redis_cache_failed", error=str(e))
            self.available = False
    
    def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        if not self.available:
            return None
        
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error("redis_get_error", key=key, error=str(e))
            return None
    
    def set(self, key: str, value: str, expire: int = 3600) -> bool:
        """Set value in Redis."""
        if not self.available:
            return False
        
        try:
            self.client.setex(key, expire, value)
            return True
        except Exception as e:
            logger.error("redis_set_error", key=key, error=str(e))
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self.available:
            return False
        
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error("redis_delete_error", key=key, error=str(e))
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.available:
            return False
        
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error("redis_exists_error", key=key, error=str(e))
            return False
    
    def flush_all(self) -> bool:
        """Flush all Redis cache."""
        if not self.available:
            return False
        
        try:
            self.client.flushdb()
            return True
        except Exception as e:
            logger.error("redis_flush_error", error=str(e))
            return False


class MemoryCache(CacheBackend):
    """In-memory cache backend (development)."""
    
    def __init__(self, max_size: int = 1000):
        """Initialize in-memory cache."""
        self.cache: dict[str, tuple[str, float]] = {}
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[str]:
        """Get value from memory cache."""
        if key not in self.cache:
            return None
        
        value, expiry = self.cache[key]
        
        # Check expiry
        if time.time() > expiry:
            del self.cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: str, expire: int = 3600) -> bool:
        """Set value in memory cache."""
        # Simple eviction if cache is full
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        expiry = time.time() + expire
        self.cache[key] = (value, expiry)
        return True
    
    def delete(self, key: str) -> bool:
        """Delete key from memory cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        return self.get(key) is not None
    
    def flush_all(self) -> bool:
        """Flush all memory cache."""
        self.cache.clear()
        return True


class CacheManager:
    """Unified cache manager."""
    
    def __init__(self, backend: Optional[CacheBackend] = None):
        """Initialize cache manager."""
        self.backend = backend or MemoryCache()
    
    def get(self, key: str) -> Optional[Any]:
        """Get deserialized value from cache."""
        try:
            value = self.backend.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set serialized value in cache."""
        try:
            json_value = json.dumps(value, default=str)
            return self.backend.set(key, json_value, expire)
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        return self.backend.delete(key)
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self.backend.exists(key)
    
    def flush_all(self) -> bool:
        """Flush all cache."""
        return self.backend.flush_all()
    
    def cached(
        self,
        expire: int = 3600,
        key_prefix: str = ""
    ) -> Callable:
        """Decorator for caching function results."""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                # Generate cache key
                cache_key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
                
                # Check cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    logger.debug("cache_hit", function=func.__name__)
                    return cached_result
                
                # Call function and cache result
                logger.debug("cache_miss", function=func.__name__)
                result = func(*args, **kwargs)
                self.set(cache_key, result, expire)
                
                return result
            
            return wrapper
        
        return decorator


# Query cache patterns
class QueryCache:
    """Specialized caching for database queries."""
    
    # Cache TTL by entity type
    DEFAULT_TTL = 300  # 5 minutes
    USER_TTL = 600  # 10 minutes
    CONVERSATION_TTL = 300  # 5 minutes
    MEMORY_TTL = 3600  # 1 hour
    
    def __init__(self, cache_manager: CacheManager):
        """Initialize query cache."""
        self.cache = cache_manager
    
    def get_user_key(self, user_id: str) -> str:
        """Generate cache key for user."""
        return f"user:{user_id}"
    
    def get_conversation_key(self, conversation_id: str) -> str:
        """Generate cache key for conversation."""
        return f"conversation:{conversation_id}"
    
    def get_messages_key(self, conversation_id: str) -> str:
        """Generate cache key for conversation messages."""
        return f"messages:{conversation_id}"
    
    def get_memory_search_key(self, query: str) -> str:
        """Generate cache key for memory search."""
        return f"memory_search:{query}"
    
    def invalidate_conversation(self, conversation_id: str) -> None:
        """Invalidate conversation cache."""
        self.cache.delete(self.get_conversation_key(conversation_id))
        self.cache.delete(self.get_messages_key(conversation_id))
    
    def invalidate_user(self, user_id: str) -> None:
        """Invalidate user cache."""
        self.cache.delete(self.get_user_key(user_id))


# Singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create cache manager instance."""
    global _cache_manager
    
    if _cache_manager is None:
        try:
            # Try to use Redis
            redis_cache = RedisCache()
            if redis_cache.available:
                _cache_manager = CacheManager(redis_cache)
            else:
                _cache_manager = CacheManager(MemoryCache())
        except Exception:
            _cache_manager = CacheManager(MemoryCache())
    
    return _cache_manager
