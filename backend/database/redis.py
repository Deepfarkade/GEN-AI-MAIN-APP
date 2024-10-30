import aioredis
from core.config import settings
import logging

class RedisClient:
    redis = None

    @classmethod
    async def connect_redis(cls):
        try:
            cls.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            # Verify connection
            await cls.redis.ping()
            logging.info("Successfully connected to Redis")
        except Exception as e:
            logging.error(f"Redis connection error: {e}")
            cls.redis = None  # Don't raise error, allow app to work without caching

    @classmethod
    async def close_redis(cls):
        if cls.redis:
            await cls.redis.close()
            logging.info("Redis connection closed")

    @classmethod
    async def get_cache(cls, key: str):
        if cls.redis:
            try:
                return await cls.redis.get(key)
            except:
                return None
        return None

    @classmethod
    async def set_cache(cls, key: str, value: str, ttl: int = None):
        if cls.redis:
            try:
                if ttl is None:
                    ttl = settings.REDIS_TTL
                await cls.redis.set(key, value, ex=ttl)
            except:
                pass