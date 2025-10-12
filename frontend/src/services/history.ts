import type { Message, Conversation } from '../types';

const STORAGE_KEY = 'chat_history';
const MAX_CONVERSATIONS = 50;

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

class HistoryService {
  private getStoredHistory(): ConversationWithMessages[] {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return [];
      
      const parsed = JSON.parse(stored);
      // Convert timestamp strings back to Date objects
      return parsed.map((conv: any) => ({
        ...conv,
        timestamp: new Date(conv.timestamp),
        messages: conv.messages.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        })),
      }));
    } catch (error) {
      console.error('Error loading chat history:', error);
      return [];
    }
  }

  private saveHistory(conversations: ConversationWithMessages[]): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch (error) {
      console.error('Error saving chat history:', error);
    }
  }

  /**
   * Get all conversations sorted by most recent first
   */
  getAllConversations(): Conversation[] {
    const history = this.getStoredHistory();
    return history
      .map(({ id, title, lastMessage, timestamp, contextType }) => ({
        id,
        title,
        lastMessage,
        timestamp,
        contextType,
      }))
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }

  /**
   * Get a specific conversation with all messages
   */
  getConversation(id: string): ConversationWithMessages | null {
    const history = this.getStoredHistory();
    return history.find(conv => conv.id === id) || null;
  }

  /**
   * Save current conversation (creates new or updates existing)
   */
  saveConversation(
    conversationId: string,
    messages: Message[],
    title?: string
  ): void {
    if (messages.length === 0) return;

    const history = this.getStoredHistory();
    const existingIndex = history.findIndex(conv => conv.id === conversationId);

    // Generate title from first user message if not provided
    const conversationTitle =
      title ||
      messages.find(m => m.role === 'user')?.content.slice(0, 50) + '...' ||
      'New Conversation';

    const lastMessage = messages[messages.length - 1]?.content.slice(0, 100);

    const conversation: ConversationWithMessages = {
      id: conversationId,
      title: conversationTitle,
      lastMessage,
      timestamp: new Date(),
      messages: messages.map(msg => ({
        ...msg,
        // Remove streaming flag from stored messages
        streaming: undefined,
      })),
    };

    if (existingIndex >= 0) {
      // Update existing conversation
      history[existingIndex] = conversation;
    } else {
      // Add new conversation
      history.unshift(conversation);
      
      // Keep only MAX_CONVERSATIONS most recent
      if (history.length > MAX_CONVERSATIONS) {
        history.splice(MAX_CONVERSATIONS);
      }
    }

    this.saveHistory(history);
  }

  /**
   * Delete a conversation
   */
  deleteConversation(id: string): void {
    const history = this.getStoredHistory();
    const filtered = history.filter(conv => conv.id !== id);
    this.saveHistory(filtered);
  }

  /**
   * Clear all history
   */
  clearHistory(): void {
    localStorage.removeItem(STORAGE_KEY);
  }

  /**
   * Search conversations by text
   */
  searchConversations(query: string): Conversation[] {
    const history = this.getStoredHistory();
    const lowerQuery = query.toLowerCase();

    return history
      .filter(conv => {
        // Search in title
        if (conv.title.toLowerCase().includes(lowerQuery)) return true;
        
        // Search in messages
        return conv.messages.some(msg =>
          msg.content.toLowerCase().includes(lowerQuery)
        );
      })
      .map(({ id, title, lastMessage, timestamp, contextType }) => ({
        id,
        title,
        lastMessage,
        timestamp,
        contextType,
      }))
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }
}

export const historyService = new HistoryService();
