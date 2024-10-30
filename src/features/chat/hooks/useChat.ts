import { useState, useCallback, useEffect } from 'react';
import { Message } from '../types';
import { ChatService } from '../services/chatService';
import { useAuth } from '../../auth/context/AuthContext';

export function useChat() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch chat history when component mounts
  useEffect(() => {
    if (user) {
      const fetchHistory = async () => {
        try {
          setIsLoading(true);
          const history = await ChatService.getChatHistory();
          setMessages(history);
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Failed to load chat history');
        } finally {
          setIsLoading(false);
        }
      };

      fetchHistory();
    }
  }, [user]);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    try {
      setIsLoading(true);
      setError(null);

      // Add user message immediately
      const userMessage: Message = {
        id: Date.now().toString(),
        content,
        role: 'user',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, userMessage]);

      // Send to backend and get response
      const response = await ChatService.sendMessage(content);
      
      // Add bot response
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.text,
        role: 'assistant',
        timestamp: new Date(response.timestamp)
      };
      
      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  return {
    messages,
    isLoading,
    error,
    sendMessage
  };
}