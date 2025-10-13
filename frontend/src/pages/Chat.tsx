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
  const [activeTab, setActiveTab] = useState<'chat' | 'history'>('chat');
  const [showHubSpotReconnect, setShowHubSpotReconnect] = useState(false);

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
        },
        messages, // Pass conversation history
        (reconnectMessage) => {
          // HubSpot reconnect required
          console.warn('HubSpot reconnect required:', reconnectMessage);
          setShowHubSpotReconnect(true);
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
      <header className="bg-white border-b border-gray-200 px-3 sm:px-6 py-3 sm:py-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          {/* Top row: Logo, Tabs, and New Thread */}
          <div className="flex items-center justify-between sm:justify-start gap-2 sm:gap-4">
            <h1 className="text-lg sm:text-xl font-semibold text-gray-900 whitespace-nowrap">Ask Anything</h1>
            
            {/* Tabs */}
            <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
              <button 
                onClick={() => setActiveTab('chat')}
                className={`px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-medium rounded-md transition-colors ${
                  activeTab === 'chat' 
                    ? 'text-gray-900 bg-white shadow-sm' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                Chat
              </button>
              <button 
                onClick={() => setActiveTab('history')}
                className={`px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-medium rounded-md transition-colors ${
                  activeTab === 'history' 
                    ? 'text-gray-900 bg-white shadow-sm' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                History
              </button>
            </div>

            {/* New thread button - icon only on mobile */}
            <button
              onClick={handleNewThread}
              className="flex items-center justify-center sm:space-x-2 px-2 sm:px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              title="New thread"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span className="hidden sm:inline">New thread</span>
            </button>
          </div>

          {/* Bottom row on mobile, Right side on desktop: User menu */}
          <div className="flex items-center justify-between sm:justify-end gap-2 sm:gap-4">
            {/* Connect HubSpot button */}
            <button
              onClick={connectHubSpot}
              className="flex items-center space-x-1.5 sm:space-x-2 px-2.5 sm:px-3 py-1.5 text-xs sm:text-sm font-medium text-white bg-orange-500 hover:bg-orange-600 rounded-lg transition-colors"
              title="Connect HubSpot CRM"
            >
              <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
              </svg>
              <span>HubSpot</span>
            </button>

            {/* User info and logout */}
            <div className="flex items-center gap-2 sm:gap-3">
              {user.picture && (
                <img
                  src={user.picture}
                  alt={user.name || user.email}
                  className="w-7 h-7 sm:w-8 sm:h-8 rounded-full"
                />
              )}
              <div className="text-xs sm:text-sm hidden sm:block">
                <div className="font-medium text-gray-900 truncate max-w-[150px]">{user.name || user.email}</div>
              </div>
              <button
                onClick={logout}
                className="text-xs sm:text-sm text-gray-600 hover:text-gray-900 whitespace-nowrap"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* HubSpot connection banner - only show if not connected */}
      {!user.hubspot_connected && (
        <div className="bg-orange-50 border-b border-orange-200 px-3 sm:px-6 py-2 sm:py-3">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 sm:gap-0 max-w-4xl mx-auto">
            <div className="flex items-center gap-2 sm:gap-3">
              <svg className="w-4 h-4 sm:w-5 sm:h-5 text-orange-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <p className="text-xs sm:text-sm text-orange-800">
                <span className="font-medium">Connect HubSpot CRM</span> to enable full client management features
              </p>
            </div>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <button
                onClick={connectHubSpot}
                className="w-full sm:w-auto px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-medium text-orange-700 bg-white border border-orange-300 rounded-lg hover:bg-orange-50 transition-colors"
              >
                Connect HubSpot
              </button>
            </div>
          </div>
        </div>
      )}

      {/* HubSpot reconnect banner - show when token expired */}
      {showHubSpotReconnect && (
        <div className="bg-red-50 border-b border-red-200 px-3 sm:px-6 py-2 sm:py-3">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 sm:gap-0 max-w-4xl mx-auto">
            <div className="flex items-center gap-2 sm:gap-3">
              <svg className="w-4 h-4 sm:w-5 sm:h-5 text-red-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <p className="text-xs sm:text-sm text-red-800">
                <span className="font-medium">HubSpot authentication expired.</span> Please reconnect your HubSpot account to continue using CRM features.
              </p>
            </div>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <button
                onClick={() => setShowHubSpotReconnect(false)}
                className="text-red-600 hover:text-red-800 p-1"
                title="Dismiss"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
              <button
                onClick={() => {
                  setShowHubSpotReconnect(false);
                  connectHubSpot();
                }}
                className="w-full sm:w-auto px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
              >
                Reconnect HubSpot
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
      {activeTab === 'chat' ? (
        <>
          <ChatWindow
            messages={messages}
            isLoading={isStreaming}
            contextLabel={currentConversationId ? "Current conversation" : undefined}
            onPromptClick={handleSendMessage}
          />

          {/* Composer */}
          <Composer
            onSend={handleSendMessage}
            disabled={isStreaming}
            placeholder="Ask anything about your meetings..."
          />
        </>
      ) : (
        <div className="flex-1 overflow-y-auto bg-white">
          <div className="max-w-4xl mx-auto px-6 py-8">
            <div className="text-center py-16">
              <svg
                className="mx-auto w-16 h-16 text-gray-300 mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                History Coming Soon
              </h3>
              <p className="text-gray-600 max-w-md mx-auto mb-6">
                Your conversation history will appear here. This feature is being developed and will be available soon.
              </p>
              <button
                onClick={() => setActiveTab('chat')}
                className="px-4 py-2 text-sm font-medium text-white bg-orange-500 hover:bg-orange-600 rounded-lg transition-colors"
              >
                Back to Chat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
