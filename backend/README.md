# Financial Advisor AI - Backend

Backend service for Financial Advisor AI, built with FastAPI, PostgreSQL, and OpenAI LLMs.

## Features
- FastAPI REST API
- Gmail, Google Calendar, and HubSpot CRM integrations
- OAuth2 authentication (Google, HubSpot)
- RAG (Retrieval-Augmented Generation) with pgvector
- Background task processing
- Memory rules engine

## Getting Started (Development)

### Prerequisites
- Python 3.13+
- Docker & Docker Compose
- PostgreSQL (local or Docker)
- OpenAI API key
- Google Cloud credentials (for Gmail/Calendar)
- HubSpot developer credentials (optional)

### 1. Clone the repository
```bash
git clone https://github.com/Amilcarpio/financial-advisor-ai-app.git
cd financial-advisor-ai-app/backend
```

### 2. Configure environment variables
Copy the example file and fill in your credentials:
```bash
cp .env.example .env
```

Example `.env.example`:
```env
APP_NAME=Financial Advisor AI Backend
APP_ENV=development
APP_DEBUG=true

DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD_HERE@localhost:5432/financial_advisor
AUTO_CREATE_PGVECTOR_EXTENSION=true

GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

HUBSPOT_CLIENT_ID=your_hubspot_client_id_here
HUBSPOT_CLIENT_SECRET=your_hubspot_client_secret_here
HUBSPOT_REDIRECT_URI=http://localhost:8000/api/auth/hubspot/callback

SECRET_KEY=your_secret_key_for_jwt_signing_min_32_chars
FRONTEND_URL=http://localhost:5173

OPENAI_API_KEY=your_openai_api_key_here
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### 3. Start services (with Docker Compose)
```bash
docker-compose -f docker-compose.dev.yml up --build
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### 4. Database migrations
```bash
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

## Development Tips
- All secrets must be set via `.env` (never commit real secrets)
- Use the provided `.env.example` as a template
- For OAuth, register your app in Google Cloud and HubSpot developer portal
- For production/deployment, see the confidential `DEPLOYMENT.md` (not in repo)

## License
Proprietary and confidential. Unauthorized copying or distribution is prohibited.

