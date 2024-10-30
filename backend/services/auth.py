from datetime import datetime, timedelta
from fastapi import HTTPException, status
from core.config import settings
from database.mongodb import MongoDB
from database.redis import RedisClient
from passlib.context import CryptContext
from jose import jwt
from models.user import UserCreate, UserInDB, UserResponse
import logging

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self):
        self.users_collection = "users"

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    async def get_user_by_email(self, email: str):
        users = await MongoDB.get_collection(self.users_collection)
        return await users.find_one({"email": email})

    async def create_user(self, user: UserCreate) -> UserResponse:
        users = await MongoDB.get_collection(self.users_collection)
        
        if await self.get_user_by_email(user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        user_dict = user.model_dump()
        user_dict["hashed_password"] = self.get_password_hash(user_dict.pop("password"))
        user_dict["created_at"] = datetime.utcnow()
        
        result = await users.insert_one(user_dict)
        user_dict["id"] = str(result.inserted_id)
        
        return UserResponse(**user_dict)

    async def authenticate_user(self, email: str, password: str):
        user = await self.get_user_by_email(email)
        if not user:
            return False
        if not self.verify_password(password, user["hashed_password"]):
            return False
        return user

    async def create_access_token(self, data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    async def send_password_reset_email(self, email: str) -> None:
        try:
            users = await MongoDB.get_collection(self.users_collection)
            user = await users.find_one({"email": email})
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Generate reset token
            reset_token = jwt.encode(
                {
                    "sub": email,
                    "exp": datetime.utcnow() + timedelta(hours=1),
                    "type": "reset"
                },
                settings.SECRET_KEY,
                algorithm=settings.ALGORITHM
            )
            
            # Store reset token in Redis with expiration
            await RedisClient.redis.set(
                f"reset_token:{email}",
                reset_token,
                ex=3600  # 1 hour expiration
            )
            
            # In production, send email with reset link
            # For development, just return success
            return reset_token
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process password reset: {str(e)}"
            )

    async def reset_password(self, token: str, new_password: str) -> None:
        try:
            # Verify token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            
            email = payload.get("sub")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token"
                )
            
            # Verify token in Redis
            stored_token = await RedisClient.redis.get(f"reset_token:{email}")
            if not stored_token or stored_token != token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired token"
                )
            
            # Update password
            users = await MongoDB.get_collection(self.users_collection)
            hashed_password = self.get_password_hash(new_password)
            
            result = await users.update_one(
                {"email": email},
                {"$set": {"hashed_password": hashed_password}}
            )
            
            if result.modified_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Remove reset token from Redis
            await RedisClient.redis.delete(f"reset_token:{email}")
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )