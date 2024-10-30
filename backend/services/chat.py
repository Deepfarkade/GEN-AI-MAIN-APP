from typing import List, Optional
from fastapi import HTTPException, status
from models.chat import ChatMessage, ChatResponse, ChatSession
from database.mongodb import MongoDB
from datetime import datetime
from bson import ObjectId
import logging
from .ai_service import AIService

class ChatService:
    def __init__(self):
        self.sessions_collection = "chat_sessions"
        self.messages_collection = "chat_messages"
        self.ai_service = AIService.get_instance()

    async def create_session(self, user_id: str) -> ChatSession:
        try:
            sessions = await MongoDB.get_collection(self.sessions_collection)
            
            session = ChatSession(
                id=str(ObjectId()),
                title="New Analysis",
                user_id=str(user_id),
                timestamp=datetime.utcnow(),
                messages=[
                    ChatMessage(
                        id=str(ObjectId()),
                        text="Hello! How can I help you with supply chain analysis today?",
                        sender="bot",
                        timestamp=datetime.utcnow()
                    )
                ]
            )
            
            await sessions.insert_one(session.model_dump())
            return session
        except Exception as e:
            logging.error(f"Failed to create chat session: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create chat session"
            )

    async def process_message(self, text: str, session_id: str, user: dict) -> ChatResponse:
        try:
            sessions = await MongoDB.get_collection(self.sessions_collection)
            
            # Verify session exists and belongs to user
            session = await sessions.find_one({
                "id": session_id,
                "user_id": str(user["_id"])
            })
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )
            
            # Save user message
            user_message = ChatMessage(
                id=str(ObjectId()),
                text=text,
                sender="user",
                session_id=session_id,
                timestamp=datetime.utcnow()
            )
            
            # Get AI response
            ai_response_text = await self.ai_service.get_ai_response(text, str(user["_id"]))
            
            # Create response object
            response = ChatResponse(
                id=str(ObjectId()),
                text=ai_response_text,
                sender="bot",
                session_id=session_id,
                timestamp=datetime.utcnow()
            )
            
            # Update session with messages
            await sessions.update_one(
                {"id": session_id},
                {
                    "$push": {"messages": {
                        "$each": [
                            user_message.model_dump(),
                            response.model_dump()
                        ]
                    }},
                    "$set": {
                        "last_message": response.text,
                        "timestamp": datetime.utcnow()
                    }
                }
            )
            
            return response
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Failed to process message: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process message"
            )

    async def get_user_sessions(self, user_id: str) -> List[ChatSession]:
        try:
            sessions = await MongoDB.get_collection(self.sessions_collection)
            cursor = sessions.find({"user_id": user_id}).sort("timestamp", -1)
            return [ChatSession(**session) async for session in cursor]
        except Exception as e:
            logging.error(f"Failed to get user sessions: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch chat sessions"
            )

    async def get_session_messages(self, session_id: str, user_id: str) -> List[ChatMessage]:
        try:
            sessions = await MongoDB.get_collection(self.sessions_collection)
            session = await sessions.find_one({
                "id": session_id,
                "user_id": user_id
            })
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )
                
            return [ChatMessage(**msg) for msg in session.get("messages", [])]
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Failed to get session messages: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch session messages"
            )