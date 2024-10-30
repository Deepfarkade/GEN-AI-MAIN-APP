from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings
import logging

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect_db(cls):
        try:
            if cls.client is None:
                cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
                cls.db = cls.client[settings.MONGODB_DB]
                # Verify connection
                await cls.client.admin.command('ping')
                logging.info("Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"MongoDB connection error: {e}")
            raise

    @classmethod
    async def close_db(cls):
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None
            logging.info("MongoDB connection closed")

    @classmethod
    async def get_collection(cls, collection_name: str):
        if cls.db is None:
            await cls.connect_db()
        return cls.db[collection_name]

    @classmethod
    def is_connected(cls) -> bool:
        return cls.client is not None and cls.db is not None