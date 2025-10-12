export interface User {
  id: string;
  email: string;
  name?: string;
  picture?: string;
  hubspot_connected?: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
  sources?: Source[];
  streaming?: boolean;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
  result?: any;
  status: 'pending' | 'running' | 'completed' | 'failed';
}

export interface Source {
  id: string;
  type: 'email' | 'contact' | 'note';
  title: string;
  snippet: string;
  relevanceScore: number;
}

export interface Conversation {
  id: string;
  title: string;
  lastMessage?: string;
  timestamp: Date;
  contextType?: string;
}

export interface Meeting {
  id: string;
  title: string;
  startTime: Date;
  endTime: Date;
  attendees: Attendee[];
  location?: string;
  description?: string;
}

export interface Attendee {
  email: string;
  name?: string;
  avatarUrl?: string;
  responseStatus?: 'accepted' | 'declined' | 'tentative' | 'needsAction';
}

export interface Contact {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  company?: string;
  phone?: string;
  avatarUrl?: string;
  hubspotId?: string;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: any;
}
