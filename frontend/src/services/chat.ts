import { apiClient } from './api';
import type { Message, Conversation } from '../types';

export interface SendMessageRequest {
  message: string;
  conversationId?: string;
}

export interface ChatResponse {
  message: Message;
  conversationId: string;
}

export type StreamCallback = (chunk: string, done: boolean) => void;
export type ErrorCallback = (error: Error) => void;

class ChatService {
  private activeEventSource: EventSource | null = null;

  /**
   * Send a message and get streaming response via fetch (not EventSource)
   */
  async streamMessage(
    message: string,
    conversationId: string | null,
    onChunk: StreamCallback,
    onError?: ErrorCallback
  ): Promise<void> {
    try {
      const baseUrl = apiClient.getBaseUrl();
      const url = `${baseUrl}/api/chat`;
      
      // Close any existing connection
      this.closeStream();

      // Use fetch with streaming
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'include',
        body: JSON.stringify({
          message,
          stream: true,
          conversation_history: [],
          source_type: null,
          max_context_chunks: 5,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Read the streaming response
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('Response body is not readable');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          onChunk('', true);
          break;
        }

        // Decode chunk
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));
              
              if (event.type === 'content') {
                // Regular text content
                onChunk(event.data || '', false);
              } else if (event.type === 'function_call') {
                // Tool calling notification
                onChunk(`\n[Using tool: ${event.data.name}]\n`, false);
              } else if (event.type === 'finish') {
                // Stream finished
                onChunk('', true);
                return;
              } else if (event.type === 'error') {
                // Error from backend
                console.error('Backend error:', event.data);
                if (onError) {
                  onError(new Error(event.data));
                }
                return;
              }
              // Ignore 'sources' type for now
            } catch (err) {
              console.error('Error parsing SSE data:', err);
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
      if (onError) {
        onError(error as Error);
      }
      throw error;
    }
  }

  /**
   * Close active stream
   */
  closeStream(): void {
    if (this.activeEventSource) {
      this.activeEventSource.close();
      this.activeEventSource = null;
    }
  }

  /**
   * Send message without streaming (fallback)
   */
  async sendMessage(data: SendMessageRequest): Promise<ChatResponse> {
    return apiClient.post<ChatResponse>('/api/chat', data);
  }

  /**
   * Get conversation history
   */
  async getConversations(): Promise<Conversation[]> {
    return apiClient.get<Conversation[]>('/api/conversations');
  }

  /**
   * Get messages for a conversation
   */
  async getMessages(conversationId: string): Promise<Message[]> {
    return apiClient.get<Message[]>(`/api/conversations/${conversationId}/messages`);
  }

  /**
   * Create a new conversation
   */
  async createConversation(title?: string): Promise<Conversation> {
    return apiClient.post<Conversation>('/api/conversations', { title });
  }

  /**
   * Delete a conversation
   */
  async deleteConversation(conversationId: string): Promise<void> {
    return apiClient.delete(`/api/conversations/${conversationId}`);
  }
}

export const chatService = new ChatService();
