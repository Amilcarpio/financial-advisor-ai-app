# Financial Advisor AI App

An intelligent CRM assistant powered by AI that helps financial advisors manage clients, emails, meetings, and tasks through natural conversation.

## Features

### Core Capabilities
- **AI-Powered Chat Interface** - Natural language interaction with your CRM data
- **Google OAuth Integration** - Secure authentication with Google accounts
- **HubSpot CRM Integration** - Full integration with HubSpot contacts, deals, and notes
- **Email & Calendar Sync** - Automatic sync of Gmail emails and Google Calendar events
- **Intelligent RAG (Retrieval-Augmented Generation)** - Context-aware responses using vector embeddings
- **Memory Rules** - Create persistent AI memory rules for personalized interactions
- **Task Management** - Create and track tasks with natural language
- **Real-time Streaming** - Live streaming responses for better UX

### Technical Features
- **Responsive Design** - Mobile-first UI that works on all devices
- **Vector Search** - pgvector-powered semantic search across emails and CRM data
- **Background Processing** - Async task processing for email/calendar sync
- **Rate Limiting** - Built-in API rate limiting and security features
- **OAuth 2.0** - Secure token management with refresh token rotation
- **Observability** - Comprehensive logging and error tracking

## Architecture

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL + pgvector** - Relational database with vector search
- **SQLAlchemy** - ORM for database operations
- **OpenAI API** - GPT-4 for conversational AI
- **Docker** - Containerized deployment

### Frontend
- **React 18** - Modern React with hooks
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Router v6** - Client-side routing

## Prerequisites

- **Docker & Docker Compose** - For running PostgreSQL and backend
- **Node.js 18+** - For frontend development
- **Python 3.13+** - For backend development (if running locally)
- **Google Cloud Project** - For OAuth and Gmail/Calendar APIs
- **HubSpot Account** - For CRM integration (optional)
- **OpenAI API Key** - For AI capabilities

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Amilcarpio/financial-advisor-ai-app.git
cd financial-advisor-ai-app
```

### 2. Backend Setup

```bash
cd backend

# Copy environment file
cp .env.example .env

# Edit .env with your credentials:
# - OPENAI_API_KEY
# - GOOGLE_OAUTH_CLIENT_ID
# - GOOGLE_OAUTH_CLIENT_SECRET
# - HUBSPOT_CLIENT_ID (optional)
# - HUBSPOT_CLIENT_SECRET (optional)

# Start services with Docker
docker-compose up -d

# Check logs
docker-compose logs -f backend
```

Backend will be available at `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

### 4. OAuth Setup

Follow the detailed instructions in [`backend/OAUTH_SETUP.md`](backend/OAUTH_SETUP.md) to configure:
- Google OAuth credentials
- Gmail API access
- Google Calendar API access
- HubSpot OAuth credentials (optional)

## Project Structure

```
financial-advisor-ai-app/
├── backend/                      # FastAPI backend
│   ├── app/
│   │   ├── api/                 # API route handlers
│   │   │   ├── auth_google.py   # Google OAuth
│   │   │   ├── auth_hubspot.py  # HubSpot OAuth
│   │   │   ├── chat.py          # Chat streaming endpoint
│   │   │   ├── rules.py         # Memory rules
│   │   │   └── ...
│   │   ├── core/                # Core configuration
│   │   │   ├── config.py        # Settings
│   │   │   ├── database.py      # Database setup
│   │   │   ├── security.py      # Security utilities
│   │   │   └── ...
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── contact.py
│   │   │   ├── email.py
│   │   │   └── ...
│   │   ├── services/            # Business logic
│   │   │   ├── tools.py         # AI function tools
│   │   │   ├── rag.py           # Vector search
│   │   │   ├── gmail_sync.py    # Gmail integration
│   │   │   ├── calendar_sync.py # Calendar integration
│   │   │   ├── hubspot_sync.py  # HubSpot integration
│   │   │   └── ...
│   │   └── utils/               # Utility functions
│   ├── migrations/              # Alembic migrations
│   ├── docker-compose.yml       # Docker services
│   ├── Dockerfile              # Backend container
│   ├── requirements.txt        # Python dependencies
│   └── README.md               # Backend documentation
│
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── Composer.tsx
│   │   │   └── MessageBubble.tsx
│   │   ├── pages/              # Page components
│   │   │   ├── Chat.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── AuthCallback.tsx
│   │   │   └── NotFound.tsx
│   │   ├── services/           # API clients
│   │   │   ├── api.ts
│   │   │   ├── auth.ts
│   │   │   ├── chat.ts
│   │   │   └── history.ts
│   │   ├── hooks/              # Custom hooks
│   │   │   └── useAuth.tsx
│   │   ├── types/              # TypeScript types
│   │   └── App.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── README.md               # Frontend documentation
│
└── README.md                    # This file
```

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```bash
# API Keys
OPENAI_API_KEY=sk-...

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# HubSpot OAuth (optional)
HUBSPOT_CLIENT_ID=...
HUBSPOT_CLIENT_SECRET=...
HUBSPOT_REDIRECT_URI=http://localhost:8000/api/auth/hubspot/callback

# Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/financial_advisor

# Security
SECRET_KEY=your-secret-key-here
FRONTEND_URL=http://localhost:5173

# Optional
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## Key Features Explained

### 1. AI Chat with Function Calling
The AI can execute real actions in your CRM:
- Search contacts and emails
- Update contact information
- Create notes and tasks
- Query calendar events
- Search HubSpot deals

### 2. Vector Search (RAG)
All emails and CRM data are embedded and searchable:
- Semantic search across all your data
- Context-aware AI responses
- Automatic relevance ranking

### 3. Memory Rules
Create persistent instructions for the AI:
```
When someone mentions baseball, search for clients who play baseball
Always check calendar before scheduling meetings
Prioritize contacts with recent activity
```

### 4. OAuth Integration
Secure authentication flow:
1. User logs in with Google
2. Grants access to Gmail and Calendar
3. Optionally connects HubSpot
4. Secure token storage with httpOnly cookies

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Manual Testing
1. Login with Google account
2. Try example prompts:
   - "Who mentioned their kid plays baseball?"
   - "Schedule an appointment with Sara Smith"
   - "What deals are closing this month?"
3. Connect HubSpot and test CRM features
4. Create memory rules and verify they work

## Deployment

### Production Build

#### Backend
```bash
cd backend
docker build -t financial-advisor-backend .
docker run -p 8000:8000 --env-file .env financial-advisor-backend
```

#### Frontend
```bash
cd frontend
npm run build
# Serve the dist/ folder with any static file server
```

### Environment Considerations
- Update CORS settings in `backend/app/main.py`
- Set production OAuth redirect URIs
- Use secure SECRET_KEY
- Enable HTTPS
- Configure rate limits
- Set up monitoring/logging

## Security

- **OAuth 2.0** with PKCE flow
- **httpOnly cookies** for session tokens
- **Refresh token rotation** for security
- **Rate limiting** on all endpoints
- **PII redaction** in logs
- **SQL injection protection** via SQLAlchemy
- **CORS** configuration
- **Input validation** on all endpoints

## Troubleshooting

### Common Issues

**Backend won't start**
- Check Docker is running: `docker ps`
- View logs: `docker-compose logs backend`
- Verify .env file exists and is valid

**OAuth errors**
- Verify redirect URIs match exactly
- Check OAuth credentials are correct
- Ensure APIs are enabled in Google Cloud Console

**Database connection issues**
- Check PostgreSQL is running: `docker-compose ps`
- Verify DATABASE_URL in .env
- Try restarting: `docker-compose restart db`

**Frontend can't connect to backend**
- Verify backend is running on port 8000
- Check CORS settings in backend/app/main.py
- Verify VITE_API_URL in frontend

## Documentation

- [Backend Documentation](backend/README.md)
- [Frontend Documentation](frontend/README.md)
- [OAuth Setup Guide](backend/OAUTH_SETUP.md)
- [API Documentation](http://localhost:8000/docs) - Available when backend is running

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is private and proprietary.

## 👥 Authors

- **Amilcar Pio** - Initial work - [@Amilcarpio](https://github.com/Amilcarpio)

## Acknowledgments

- OpenAI for GPT-4 API
- HubSpot for CRM integration
- Google for OAuth and API services
- FastAPI and React communities

## Support

For issues, questions, or support:
- Open an issue on GitHub
- Email: amilcar.pio@gmail.com

---

**Built with ❤️ using FastAPI, React, and AI**
