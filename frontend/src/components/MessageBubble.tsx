import { format } from 'date-fns';
import type { Message } from '../types';
import DOMPurify from 'dompurify';

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  // Sanitize content to prevent XSS
  const sanitizedContent = DOMPurify.sanitize(message.content, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'br', 'p', 'ul', 'ol', 'li', 'code', 'pre'],
    ALLOWED_ATTR: ['href', 'target', 'rel'],
  });

  if (isSystem) {
    return (
      <div className="flex justify-center my-4">
        <div className="bg-gray-100 rounded-full px-4 py-2 text-xs text-gray-600">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-gray-200 text-gray-900'
            : 'bg-white border border-gray-200 text-gray-900'
        }`}
      >
        {/* Message content */}
        <div
          className="prose prose-sm max-w-none"
          dangerouslySetInnerHTML={{ __html: sanitizedContent }}
        />

        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.toolCalls.map((tool) => (
              <div
                key={tool.id}
                className="flex items-center space-x-2 text-xs bg-blue-50 rounded-lg px-3 py-2"
              >
                <div className="flex items-center space-x-2">
                  {tool.status === 'running' && (
                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
                  )}
                  {tool.status === 'completed' && (
                    <svg className="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                  {tool.status === 'failed' && (
                    <svg className="w-3 h-3 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                  <span className="font-medium text-blue-900">{tool.name}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3">
            <details className="group">
              <summary className="cursor-pointer text-xs text-blue-600 hover:text-blue-800 font-medium">
                View {message.sources.length} source{message.sources.length > 1 ? 's' : ''}
              </summary>
              <div className="mt-2 space-y-2">
                {message.sources.map((source) => (
                  <div
                    key={source.id}
                    className="bg-gray-50 rounded-lg p-2 text-xs border border-gray-200"
                  >
                    <div className="font-medium text-gray-900">{source.title}</div>
                    <div className="text-gray-600 mt-1">{source.snippet}</div>
                    <div className="text-gray-400 mt-1 capitalize">{source.type}</div>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}

        {/* Timestamp */}
        <div className="mt-2 text-xs text-gray-500">
          {format(new Date(message.timestamp), 'h:mm a')}
        </div>
      </div>
    </div>
  );
}
