from interpreter import interpreter
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from fastapi import HTTPException, status

class AIService:
    _instance = None
    _executor = ThreadPoolExecutor(max_workers=10)  # Limit concurrent AI calls

    def __init__(self):
        # Initialize interpreter settings
        interpreter.llm.model = "gpt-3.5-turbo"
        interpreter.llm.temperature = 0.7
        interpreter.llm.api_key = "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"
        interpreter.llm.supports_functions = True
        interpreter.custom_instructions = """
        You are 'Maddy', an AI assistant created by EY India GEN AI Engineers. Your primary focus is on:
        1. Supply chain analysis and optimization
        2. Root cause analysis (RCA)
        3. Predictive quality analysis (PQA)
        4. Data summarization and forecasting
        5. Machine learning insights

        Always maintain a professional tone while being helpful and precise in your responses.
        Focus on providing actionable insights and clear explanations.
        """

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AIService()
        return cls._instance

    async def get_ai_response(self, message: str, user_id: str) -> str:
        """
        Get AI response asynchronously using a thread pool to prevent blocking
        """
        try:
            # Run the interpreter in a separate thread to avoid blocking
            response = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._get_interpreter_response,
                message
            )
            return response
        except Exception as e:
            logging.error(f"AI Service error for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate AI response"
            )

    def _get_interpreter_response(self, message: str) -> str:
        """
        Get response from interpreter in a synchronous manner
        """
        try:
            # Use chat method for single response
            response = interpreter.chat(message)
            # Extract the last assistant message
            if isinstance(response, list):
                for msg in reversed(response):
                    if msg.get('role') == 'assistant':
                        return msg.get('content', '')
            return str(response)
        except Exception as e:
            logging.error(f"Interpreter error: {str(e)}")
            raise