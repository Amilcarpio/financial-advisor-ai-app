import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import type { Message } from '../types';

interface ChatWindowProps {
  messages: Message[];
  isLoading?: boolean;
  contextLabel?: string;
}

export default function ChatWindow({ messages, isLoading, contextLabel }: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex-1 overflow-hidden flex flex-col bg-gray-50">
      {/* Context indicator */}
      {contextLabel && (
        <div className="flex justify-center py-3 border-b border-gray-200 bg-white">
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <span>Context set to</span>
            <span className="font-medium text-gray-900">{contextLabel}</span>
            <span className="text-gray-400">•</span>
            <span className="text-gray-500">11:17am – May 13, 2025</span>
          </div>
        </div>
      )}

      {/* Messages container */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto custom-scrollbar px-4 py-6"
      >
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
                <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Start a conversation
              </h3>
              <p className="text-gray-600 max-w-md mx-auto">
                Ask me anything about your clients, emails, meetings, or ask me to help with tasks.
              </p>
              
              {/* Example prompts */}
              <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl mx-auto">
                <button className="text-left p-4 bg-white border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-sm transition-all">
                  <div className="font-medium text-gray-900 mb-1">
                    Who mentioned their kid plays baseball?
                  </div>
                  <div className="text-sm text-gray-500">
                    Search emails and CRM notes
                  </div>
                </button>
                <button className="text-left p-4 bg-white border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-sm transition-all">
                  <div className="font-medium text-gray-900 mb-1">
                    Schedule an appointment with Sara Smith
                  </div>
                  <div className="text-sm text-gray-500">
                    Check calendar and send email
                  </div>
                </button>
                <button className="text-left p-4 bg-white border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-sm transition-all">
                  <div className="font-medium text-gray-900 mb-1">
                    Why did Greg want to sell AAPL stock?
                  </div>
                  <div className="text-sm text-gray-500">
                    Find relevant context
                  </div>
                </button>
                <button className="text-left p-4 bg-white border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-sm transition-all">
                  <div className="font-medium text-gray-900 mb-1">
                    When someone emails me, create a HubSpot contact
                  </div>
                  <div className="text-sm text-gray-500">
                    Set ongoing instructions
                  </div>
                </button>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
            </>
          )}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start mb-4">
              <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>
    </div>
  );
}
