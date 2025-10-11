import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import ChatWindow from '../components/ChatWindow';
import Composer from '../components/Composer';
import { chatService } from '../services/chat';
import type { Message } from '../types';

export default function Chat() {
  const { user, loading: authLoading, logout, connectHubSpot } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [showHubSpotBanner, setShowHubSpotBanner] = useState(true);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      window.location.href = '/login';
    }
  }, [user, authLoading]);

  const handleSendMessage = async (message: string) => {
    // Add user message to UI
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsStreaming(true);
    setStreamingContent('');
    setError(null);

    try {
      // Create streaming message placeholder
      const assistantMessageId = `assistant-${Date.now()}`;
      let accumulatedContent = '';

      // Stream the response
      await chatService.streamMessage(
        message,
        currentConversationId,
        (chunk, done) => {
          if (done) {
            // Finalize the message
            const finalMessage: Message = {
              id: assistantMessageId,
              role: 'assistant',
              content: accumulatedContent,
              timestamp: new Date(),
            };

            setMessages((prev) => {
              // Remove streaming placeholder and add final message
              const filtered = prev.filter((m) => m.id !== 'streaming');
              return [...filtered, finalMessage];
            });

            setIsStreaming(false);
            setStreamingContent('');
          } else {
            // Accumulate content
            accumulatedContent += chunk;
            setStreamingContent(accumulatedContent);

            // Update or create streaming message
            setMessages((prev) => {
              const filtered = prev.filter((m) => m.id !== 'streaming');
              return [
                ...filtered,
                {
                  id: 'streaming',
                  role: 'assistant' as const,
                  content: accumulatedContent,
                  timestamp: new Date(),
                  streaming: true,
                },
              ];
            });
          }
        },
        (err) => {
          console.error('Streaming error:', err);
          setError('Failed to get response. Please try again.');
          setIsStreaming(false);
          setStreamingContent('');
        }
      );
    } catch (err) {
      console.error('Send message error:', err);
      setError('Failed to send message. Please try again.');
      setIsStreaming(false);
    }
  };

  const handleNewThread = () => {
    setMessages([]);
    setCurrentConversationId(null);
    setStreamingContent('');
    setError(null);
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold text-gray-900">Ask Anything</h1>
            
            {/* Tabs */}
            <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
              <button className="px-4 py-1.5 text-sm font-medium text-gray-900 bg-white rounded-md shadow-sm">
                Chat
              </button>
              <button className="px-4 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-900">
                History
              </button>
            </div>

            {/* New thread button */}
            <button
              onClick={handleNewThread}
              className="flex items-center space-x-2 px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>New thread</span>
            </button>
          </div>

          {/* User menu */}
          <div className="flex items-center space-x-4">
            {/* Connect HubSpot button */}
            <button
              onClick={connectHubSpot}
              className="flex items-center space-x-2 px-3 py-1.5 text-sm font-medium text-white bg-orange-500 hover:bg-orange-600 rounded-lg transition-colors"
              title="Connect HubSpot CRM"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
              </svg>
              <span>HubSpot</span>
            </button>

            {user.picture && (
              <img
                src={user.picture}
                alt={user.name || user.email}
                className="w-8 h-8 rounded-full"
              />
            )}
            <div className="text-sm">
              <div className="font-medium text-gray-900">{user.name || user.email}</div>
            </div>
            <button
              onClick={logout}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* HubSpot connection banner */}
      {showHubSpotBanner && (
        <div className="bg-orange-50 border-b border-orange-200 px-6 py-3">
          <div className="flex items-center justify-between max-w-4xl mx-auto">
            <div className="flex items-center space-x-3">
              <svg className="w-5 h-5 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <p className="text-sm text-orange-800">
                <span className="font-medium">Connect HubSpot CRM</span> to enable full client management features
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={connectHubSpot}
                className="px-4 py-1.5 text-sm font-medium text-orange-700 bg-white border border-orange-300 rounded-lg hover:bg-orange-50 transition-colors"
              >
                Connect HubSpot
              </button>
              <button
                onClick={() => setShowHubSpotBanner(false)}
                className="text-orange-600 hover:text-orange-800"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-3">
          <div className="flex items-center justify-between max-w-4xl mx-auto">
            <p className="text-sm text-red-800">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-red-800 hover:text-red-900"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Chat area */}
      <ChatWindow
        messages={messages}
        isLoading={isStreaming}
        contextLabel={currentConversationId ? "Current conversation" : undefined}
      />

      {/* Composer */}
      <Composer
        onSend={handleSendMessage}
        disabled={isStreaming}
        placeholder="Ask anything about your meetings..."
      />
    </div>
  );
}
