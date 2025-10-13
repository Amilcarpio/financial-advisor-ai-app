# Financial Advisor AI Application# Financial Advisor AI App



An intelligent financial advisory platform that leverages artificial intelligence to provide proactive assistance through automated email management, calendar coordination, and CRM integration.An intelligent CRM assistant powered by AI that helps financial advisors manage clients, emails, meetings, and tasks through natural conversation.



## Overview## Features



This application combines a FastAPI backend with a React frontend to deliver an AI-powered assistant for financial advisors. The system automatically syncs with Gmail, Google Calendar, and HubSpot CRM, using large language models to intelligently process events and execute appropriate actions based on configurable memory rules.### Core Capabilities

- **AI-Powered Chat Interface** - Natural language interaction with your CRM data

### Key Features- **Google OAuth Integration** - Secure authentication with Google accounts

- **HubSpot CRM Integration** - Full integration with HubSpot contacts, deals, and notes

- **AI-Powered Automation**: Intelligent event processing using OpenAI's language models- **Email & Calendar Sync** - Automatic sync of Gmail emails and Google Calendar events

- **Email Management**: Automatic Gmail synchronization and processing- **Intelligent RAG (Retrieval-Augmented Generation)** - Context-aware responses using vector embeddings

- **Calendar Integration**: Google Calendar event tracking and attendee notification- **Memory Rules** - Create persistent AI memory rules for personalized interactions

- **CRM Synchronization**: Bidirectional HubSpot contact and deal management- **Task Management** - Create and track tasks with natural language

- **Memory Rules**: User-defined automation rules in natural language- **Real-time Streaming** - Live streaming responses for better UX

- **RAG System**: Context-aware responses using vector similarity search

- **Real-time Updates**: WebSocket support for live notifications### Technical Features

- **OAuth2 Security**: Secure authentication with Google and HubSpot- **Responsive Design** - Mobile-first UI that works on all devices

- **Vector Search** - pgvector-powered semantic search across emails and CRM data

## Architecture- **Background Processing** - Async task processing for email/calendar sync

- **Rate Limiting** - Built-in API rate limiting and security features

### Technology Stack- **OAuth 2.0** - Secure token management with refresh token rotation

- **Observability** - Comprehensive logging and error tracking

**Backend:**

- Python 3.13## Architecture

- FastAPI web framework

- PostgreSQL database with pgvector extension### Backend

- SQLAlchemy ORM- **FastAPI** - Modern Python web framework

- OpenAI API for LLM capabilities- **PostgreSQL + pgvector** - Relational database with vector search

- OAuth2 authentication- **SQLAlchemy** - ORM for database operations

- **OpenAI API** - GPT-4 for conversational AI

**Frontend:**- **Docker** - Containerized deployment

- React 18 with TypeScript

- Vite build tool### Frontend

- TanStack Query for data fetching- **React 18** - Modern React with hooks

- Tailwind CSS for styling- **TypeScript** - Type-safe JavaScript

- Lucide React for icons- **Vite** - Fast build tool and dev server

- **Tailwind CSS** - Utility-first CSS framework

### System Components- **React Router v6** - Client-side routing



```## Prerequisites

├── backend/          # FastAPI application

│   ├── app/- **Docker & Docker Compose** - For running PostgreSQL and backend

│   │   ├── api/      # REST API endpoints- **Node.js 18+** - For frontend development

│   │   ├── core/     # Configuration and database- **Python 3.13+** - For backend development (if running locally)

│   │   ├── models/   # Database models- **Google Cloud Project** - For OAuth and Gmail/Calendar APIs

│   │   ├── services/ # Business logic- **HubSpot Account** - For CRM integration (optional)

│   │   └── utils/    # Helper functions- **OpenAI API Key** - For AI capabilities

│   └── Dockerfile

├── frontend/         # React application## Quick Start

│   ├── src/

│   │   ├── components/  # React components### 1. Clone the Repository

│   │   ├── lib/         # Utilities and API client

│   │   └── pages/       # Page components```bash

│   └── Dockerfilegit clone https://github.com/Amilcarpio/financial-advisor-ai-app.git

└── docker-compose.yml   # Development environmentcd financial-advisor-ai-app

``````



## Prerequisites### 2. Backend Setup



- Docker and Docker Compose```bash

- OpenAI API keycd backend

- Google Cloud Platform account (for Gmail and Calendar APIs)

- HubSpot developer account# Copy environment file

- Node.js 18+ (for local frontend development)cp .env.example .env

- Python 3.13+ (for local backend development)

# Edit .env with your credentials:

## Quick Start# - OPENAI_API_KEY

# - GOOGLE_OAUTH_CLIENT_ID

### 1. Clone the Repository# - GOOGLE_OAUTH_CLIENT_SECRET

# - HUBSPOT_CLIENT_ID (optional)

```bash# - HUBSPOT_CLIENT_SECRET (optional)

git clone https://github.com/yourusername/financial-advisor-ai-app.git

cd financial-advisor-ai-app# Start services with Docker

```docker-compose up -d



### 2. Configure Environment Variables# Check logs

docker-compose logs -f backend

Create a `.env` file in the `backend` directory:```



```bashBackend will be available at `http://localhost:8000`

cd backend

cp .env.example .env### 3. Frontend Setup

```

```bash

Edit `.env` with your credentials:cd frontend



```env# Install dependencies

# Applicationnpm install

APP_NAME=Financial Advisor AI

APP_ENV=development# Start development server

APP_DEBUG=truenpm run dev

SECRET_KEY=your-secret-key-min-32-characters```



# DatabaseFrontend will be available at `http://localhost:5173`

DATABASE_URL=postgresql://postgres:postgres@db:5432/financial_advisor

### 4. OAuth Setup

# OpenAI

OPENAI_API_KEY=your-openai-api-keyFollow the detailed instructions in [`backend/OAUTH_SETUP.md`](backend/OAUTH_SETUP.md) to configure:

OPENAI_CHAT_MODEL=gpt-4o-mini- Google OAuth credentials

OPENAI_EMBEDDING_MODEL=text-embedding-3-small- Gmail API access

- Google Calendar API access

# Google OAuth- HubSpot OAuth credentials (optional)

GOOGLE_CLIENT_ID=your-google-client-id

GOOGLE_CLIENT_SECRET=your-google-client-secret## Project Structure

GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

```

# HubSpot OAuthfinancial-advisor-ai-app/

HUBSPOT_CLIENT_ID=your-hubspot-client-id├── backend/                      # FastAPI backend

HUBSPOT_CLIENT_SECRET=your-hubspot-client-secret│   ├── app/

HUBSPOT_REDIRECT_URI=http://localhost:8000/api/auth/hubspot/callback│   │   ├── api/                 # API route handlers

│   │   │   ├── auth_google.py   # Google OAuth

# Frontend│   │   │   ├── auth_hubspot.py  # HubSpot OAuth

FRONTEND_URL=http://localhost:5173│   │   │   ├── chat.py          # Chat streaming endpoint

```│   │   │   ├── rules.py         # Memory rules

│   │   │   └── ...

### 3. Start the Application│   │   ├── core/                # Core configuration

│   │   │   ├── config.py        # Settings

```bash│   │   │   ├── database.py      # Database setup

docker compose up│   │   │   ├── security.py      # Security utilities

```│   │   │   └── ...

│   │   ├── models/              # SQLAlchemy models

The application will be available at:│   │   │   ├── user.py

- Frontend: http://localhost:5173│   │   │   ├── contact.py

- Backend API: http://localhost:8000│   │   │   ├── email.py

- API Documentation: http://localhost:8000/docs│   │   │   └── ...

│   │   ├── services/            # Business logic

### 4. OAuth Setup│   │   │   ├── tools.py         # AI function tools

│   │   │   ├── rag.py           # Vector search

Detailed OAuth configuration instructions can be found in:│   │   │   ├── gmail_sync.py    # Gmail integration

- Backend: `backend/OAUTH_SETUP.md`│   │   │   ├── calendar_sync.py # Calendar integration

- Frontend: `frontend/README.md`│   │   │   ├── hubspot_sync.py  # HubSpot integration

│   │   │   └── ...

## Development│   │   └── utils/               # Utility functions

│   ├── migrations/              # Alembic migrations

### Backend Development│   ├── docker-compose.yml       # Docker services

│   ├── Dockerfile              # Backend container

See `backend/README.md` for detailed backend development instructions, including:│   ├── requirements.txt        # Python dependencies

- Local development setup│   └── README.md               # Backend documentation

- Database migrations│

- API endpoint documentation├── frontend/                    # React frontend

- Testing procedures│   ├── src/

│   │   ├── components/         # React components

### Frontend Development│   │   │   ├── ChatWindow.tsx

│   │   │   ├── Composer.tsx

See `frontend/README.md` for detailed frontend development instructions, including:│   │   │   └── MessageBubble.tsx

- Component architecture│   │   ├── pages/              # Page components

- State management│   │   │   ├── Chat.tsx

- Build configuration│   │   │   ├── Login.tsx

- Deployment procedures│   │   │   ├── AuthCallback.tsx

│   │   │   └── NotFound.tsx

## Production Deployment│   │   ├── services/           # API clients

│   │   │   ├── api.ts

### Backend Deployment (Fly.io)│   │   │   ├── auth.ts

│   │   │   ├── chat.ts

The backend is configured for deployment to Fly.io:│   │   │   └── history.ts

│   │   ├── hooks/              # Custom hooks

```bash│   │   │   └── useAuth.tsx

cd backend│   │   ├── types/              # TypeScript types

fly deploy│   │   └── App.tsx

```│   ├── package.json

│   ├── vite.config.ts

See `backend/README.md` for complete deployment instructions.│   ├── tailwind.config.js

│   └── README.md               # Frontend documentation

### Frontend Deployment (GitHub Pages)│

└── README.md                    # This file

The frontend is configured for static deployment to GitHub Pages:```



```bash## 🔧 Configuration

cd frontend

npm run build### Environment Variables

npm run deploy

```#### Backend (.env)

```bash

See `frontend/README.md` for complete deployment instructions.# API Keys

OPENAI_API_KEY=sk-...

## API Documentation

# Google OAuth

Interactive API documentation is available at `/docs` when running the backend:GOOGLE_OAUTH_CLIENT_ID=...

- Swagger UI: http://localhost:8000/docsGOOGLE_OAUTH_CLIENT_SECRET=...

- ReDoc: http://localhost:8000/redocGOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/auth/google/callback



## Database Schema# HubSpot OAuth (optional)

HUBSPOT_CLIENT_ID=...

The application uses PostgreSQL with the pgvector extension for vector similarity search. Key tables include:HUBSPOT_CLIENT_SECRET=...

HUBSPOT_REDIRECT_URI=http://localhost:8000/api/auth/hubspot/callback

- `user`: User accounts and OAuth tokens

- `email`: Gmail messages# Database

- `contact`: HubSpot contactsDATABASE_URL=postgresql://postgres:postgres@db:5432/financial_advisor

- `memoryrule`: User-defined automation rules

- `task`: Background job queue# Security

- `vector_item`: Embedded documents for RAGSECRET_KEY=your-secret-key-here

FRONTEND_URL=http://localhost:5173

## Background Workers

# Optional

The system includes a background worker for processing asynchronous tasks:LOG_LEVEL=INFO

- Email synchronizationENVIRONMENT=development

- Calendar event processing```

- LLM-based event analysis

- Memory rule evaluation## Key Features Explained



## Security Considerations### 1. AI Chat with Function Calling

The AI can execute real actions in your CRM:

- All sensitive credentials must be stored in environment variables- Search contacts and emails

- OAuth2 is used for all third-party integrations- Update contact information

- JWT tokens for session management- Create notes and tasks

- CORS protection configured for production- Query calendar events

- Rate limiting on API endpoints- Search HubSpot deals



## Contributing### 2. Vector Search (RAG)

All emails and CRM data are embedded and searchable:

Contributions are welcome. Please ensure:- Semantic search across all your data

- Code follows existing style conventions- Context-aware AI responses

- All tests pass- Automatic relevance ranking

- Documentation is updated

- Environment variables are not hardcoded### 3. Memory Rules

Create persistent instructions for the AI:

## License```

When someone mentions baseball, search for clients who play baseball

Proprietary and confidential. Unauthorized copying or distribution is prohibited.Always check calendar before scheduling meetings

Prioritize contacts with recent activity

## Support```



For issues or questions, please open an issue in the GitHub repository.### 4. OAuth Integration

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
