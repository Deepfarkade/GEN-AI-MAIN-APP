from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from api.routes import auth, chat
from core.config import settings
import uvicorn
from contextlib import asynccontextmanager
from database.mongodb import MongoDB
from database.redis import RedisClient
import logging
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Startup: Connect to databases
        await MongoDB.connect_db()
        await RedisClient.connect_redis()
        logger.info("Successfully connected to databases")
        yield
    finally:
        # Shutdown: Close connections
        await MongoDB.close_db()
        await RedisClient.close_redis()
        logger.info("Database connections closed")

app = FastAPI(
    title="SmartChat API",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )