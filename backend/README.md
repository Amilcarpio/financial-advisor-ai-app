# Backend - Financial Advisor AI# Financial Advisor AI - Backend



FastAPI backend service providing AI-powered automation for financial advisors through integration with Gmail, Google Calendar, and HubSpot CRM.FastAPI-based backend with AI chat capabilities, CRM integrations, and vector search.



## Overview## Quick Start



The backend is a modern Python application built with FastAPI, featuring:### Using Docker (Recommended)

- RESTful API endpoints for all client operations

- Background worker for async task processing```bash

- PostgreSQL database with pgvector for vector search# Copy environment file

- OAuth2 authentication with Google and HubSpotcp .env.example .env

- OpenAI integration for LLM capabilities

- Memory rules system for automated event handling# Edit .env with your API keys and credentials



## Technology Stack# Start all services (PostgreSQL + Backend)

docker-compose up -d

- **Python 3.13**: Modern Python with type hints

- **FastAPI**: High-performance web framework# View logs

- **PostgreSQL + pgvector**: Vector-enabled databasedocker-compose logs -f backend

- **SQLAlchemy**: ORM for database operations

- **Pydantic**: Data validation and settings management# Stop services

- **OpenAI API**: GPT models for AI capabilitiesdocker-compose down

- **Google APIs**: Gmail and Calendar integration```

- **HubSpot API**: CRM integration

Backend will be available at `http://localhost:8000`

## Project StructureAPI documentation at `http://localhost:8000/docs`



```### Local Development (Without Docker)

backend/

├── app/1. **Install Python 3.13+** and create a virtual environment:

│   ├── api/              # API endpoint definitions   ```bash

│   │   ├── auth_google.py    # Google OAuth flow   python -m venv venv

│   │   ├── auth_hubspot.py   # HubSpot OAuth flow   source venv/bin/activate  # On Windows: venv\Scripts\activate

│   │   ├── chat.py           # Chat/conversation endpoints   ```

│   │   ├── embeddings.py     # Document embedding endpoints

│   │   ├── health.py         # Health check endpoint2. **Install dependencies:**

│   │   ├── ingest.py         # Data ingestion endpoints   ```bash

│   │   ├── rules.py          # Memory rules management   pip install -r requirements.txt

│   │   ├── tools.py          # AI tool execution endpoints   ```

│   │   └── webhooks.py       # External webhook handlers

│   ├── core/             # Core configuration3. **Setup PostgreSQL with pgvector:**

│   │   ├── config.py         # Application settings   ```bash

│   │   ├── database.py       # Database connection   # Install PostgreSQL and pgvector extension

│   │   ├── logging_config.py # Logging configuration   # On macOS with Homebrew:

│   │   ├── rate_limiting.py  # API rate limiting   brew install postgresql pgvector

│   │   └── security.py       # Security utilities   

│   ├── models/           # Database models   # Create database

│   │   ├── contact.py        # HubSpot contact model   createdb financial_advisor

│   │   ├── email.py          # Gmail message model   ```

│   │   ├── memory_rule.py    # Memory rule model

│   │   ├── task.py           # Background task model4. **Configure environment:**

│   │   ├── user.py           # User account model   ```bash

│   │   └── vector_item.py    # Vector embedding model   cp .env.example .env

│   ├── services/         # Business logic   # Edit .env with your credentials

│   │   ├── calendar_sync.py  # Google Calendar sync   ```

│   │   ├── embeddings.py     # Document embedding service

│   │   ├── gmail_sync.py     # Gmail sync service5. **Run migrations:**

│   │   ├── hubspot_sync.py   # HubSpot sync service   ```bash

│   │   ├── memory_rules.py   # Memory rules engine   alembic upgrade head

│   │   ├── openai_prompts.py # LLM prompts and tools   ```

│   │   ├── rag.py            # RAG system

│   │   ├── tasks_worker.py   # Background worker6. **Start development server:**

│   │   └── tools.py          # AI tool implementations   ```bash

│   ├── utils/            # Utility functions   uvicorn app.main:app --reload --port 8000

│   │   ├── chunking.py       # Text chunking utilities   ```

│   │   ├── oauth_helpers.py  # OAuth helper functions

│   │   └── security.py       # Security utilities## Prerequisites

│   ├── migrations/       # Database migrations

│   └── main.py           # Application entry point- Python 3.13+

├── Dockerfile            # Docker image definition- PostgreSQL 14+ with pgvector extension

├── requirements.txt      # Python dependencies- Docker & Docker Compose (for containerized deployment)

└── .env.example          # Environment variables template- OpenAI API key

```- Google OAuth credentials

- HubSpot API credentials (optional)

## Prerequisites

## Configuration

- Python 3.13+

- PostgreSQL 15+ with pgvector extension### Required Environment Variables

- Docker and Docker Compose (recommended)

- OpenAI API key```bash

- Google Cloud Platform project with OAuth credentials# API Keys

- HubSpot developer account with OAuth appOPENAI_API_KEY=sk-...



## Environment Configuration# Google OAuth

GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com

Create a `.env` file in the backend directory with the following variables:GOOGLE_OAUTH_CLIENT_SECRET=your-secret

GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

```env

# Application Settings# Database

APP_NAME=Financial Advisor AIDATABASE_URL=postgresql://postgres:postgres@localhost:5432/financial_advisor

APP_ENV=development

APP_DEBUG=true# Security

SECRET_KEY=your-secret-key-minimum-32-characters-requiredSECRET_KEY=your-secret-key-minimum-32-characters

FRONTEND_URL=http://localhost:5173

# Database

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/financial_advisor# Optional: HubSpot Integration

VECTOR_DIMENSION=1536HUBSPOT_CLIENT_ID=your-hubspot-client-id

AUTO_CREATE_PGVECTOR_EXTENSION=trueHUBSPOT_CLIENT_SECRET=your-hubspot-secret

HUBSPOT_REDIRECT_URI=http://localhost:8000/api/auth/hubspot/callback

# OpenAI```

OPENAI_API_KEY=sk-your-openai-api-key

OPENAI_CHAT_MODEL=gpt-4o-miniSee `.env.example` for all available configuration options.

OPENAI_EMBEDDING_MODEL=text-embedding-3-small

### OAuth Setup

# Google OAuth

GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.comSee [OAUTH_SETUP.md](OAUTH_SETUP.md) for detailed instructions on:

GOOGLE_CLIENT_SECRET=your-google-client-secret- Creating Google Cloud project

GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback- Enabling Gmail and Calendar APIs

- Setting up HubSpot OAuth

# HubSpot OAuth- Configuring redirect URIs

HUBSPOT_CLIENT_ID=your-hubspot-client-id

HUBSPOT_CLIENT_SECRET=your-hubspot-client-secret## Database Setup

HUBSPOT_REDIRECT_URI=http://localhost:8000/api/auth/hubspot/callback

The project uses **SQLAlchemy** with **PostgreSQL** and **pgvector** for vector search.

# Frontend URL (for CORS)

FRONTEND_URL=http://localhost:5173### Migrations with Alembic

```

```bash

## Installation# Generate a new migration after model changes

alembic revision --autogenerate -m "description of changes"

### Option 1: Docker (Recommended)

# Apply all pending migrations

```bashalembic upgrade head

# Start all services

docker compose up# Rollback last migration

alembic downgrade -1

# Run migrations

docker compose exec backend alembic upgrade head# View migration history

alembic history

# View logs```

docker compose logs -f backend

```### Database Schema



### Option 2: Local DevelopmentKey models:

- **User** - User accounts with OAuth tokens

```bash- **Contact** - HubSpot contacts

# Create virtual environment- **Email** - Gmail messages with metadata

python -m venv venv- **VectorItem** - Embedded content for semantic search

source venv/bin/activate  # On Windows: venv\Scripts\activate- **MemoryRule** - Persistent AI instructions

- **Task** - Asynchronous background tasks

# Install dependencies

pip install -r requirements.txt## Background Worker



# Start PostgreSQL (ensure pgvector is installed)The application includes a background worker for processing asynchronous tasks.

# Then run migrations

alembic upgrade head### Running the Worker



# Start the backend```bash

uvicorn app.main:app --reload --port 8000# With Docker (already running in docker-compose)

docker-compose logs -f worker

# In a separate terminal, start the worker

python -m app.services.tasks_worker# Locally

```python -m app.services.tasks_worker

```

## Database Migrations

### Worker Features

The application uses Alembic for database schema management.

- **Polling-based task processing** - Checks for new tasks every 5 seconds

```bash- **Concurrency control** - Max 10 concurrent tasks using `SELECT FOR UPDATE SKIP LOCKED`

# Create a new migration- **Exponential backoff retry** - Up to 3 attempts with increasing delays

alembic revision --autogenerate -m "description"- **Task types:**

  - Email sync from Gmail

# Apply migrations  - Calendar event sync

alembic upgrade head  - Contact creation/updates

  - Embedding generation

# Rollback last migration  - HubSpot data sync

alembic downgrade -1

### Task Monitoring

# View current migration version

alembic current```bash

# Check task status in database

# View migration historydocker exec -it financial-advisor-db psql -U postgres -d financial_advisor -c "SELECT * FROM task ORDER BY created_at DESC LIMIT 10;"

alembic history```

```

## API Endpoints

## API Endpoints

### Authentication

### Authentication- `GET /api/auth/google/start` - Initiate Google OAuth flow

- `GET /api/auth/google/callback` - Google OAuth callback

- `GET /api/auth/google` - Initiate Google OAuth flow- `GET /api/auth/hubspot/start` - Initiate HubSpot OAuth flow

- `GET /api/auth/google/callback` - Google OAuth callback- `GET /api/auth/hubspot/callback` - HubSpot OAuth callback

- `GET /api/auth/hubspot` - Initiate HubSpot OAuth flow- `GET /api/auth/me` - Get current user info

- `GET /api/auth/hubspot/callback` - HubSpot OAuth callback- `POST /api/auth/logout` - Logout user

- `POST /api/auth/refresh` - Refresh access token

- `POST /api/auth/logout` - Logout user### Chat

- `POST /api/chat/stream` - Stream chat responses with function calling

### Chat & Conversations

### Memory Rules

- `POST /api/chat/message` - Send a chat message- `GET /api/rules` - List all memory rules

- `POST /api/chat/stream` - Streaming chat endpoint- `POST /api/rules` - Create new memory rule

- `GET /api/rules/{id}` - Get specific rule

### Data Management- `PUT /api/rules/{id}` - Update rule

- `DELETE /api/rules/{id}` - Delete rule

- `POST /api/ingest/documents` - Ingest and embed documents

- `GET /api/embeddings/search` - Search embedded documents### Embeddings & RAG

- `POST /api/ingest/emails` - Manually trigger email ingestion

### Memory Rules- `POST /api/ingest/contacts` - Manually trigger contact ingestion

- `POST /api/embeddings/search` - Search embedded content

- `GET /api/rules` - List all memory rules

- `POST /api/rules` - Create a new memory rule### Health

- `PUT /api/rules/{rule_id}` - Update a memory rule- `GET /api/health` - Health check endpoint

- `DELETE /api/rules/{rule_id}` - Delete a memory rule- `GET /docs` - Interactive API documentation (Swagger UI)

- `GET /redoc` - Alternative API documentation (ReDoc)

### Webhooks

## AI Function Tools

- `POST /api/webhooks/gmail` - Gmail Pub/Sub webhook

- `POST /api/webhooks/calendar` - Google Calendar webhookThe AI can execute these functions during conversation:

- `POST /api/webhooks/hubspot` - HubSpot webhook

### Search Tools

### Health & Status- `search_emails` - Semantic search across all emails

- `search_contacts` - Search HubSpot contacts

- `GET /health` - Health check endpoint- `search_deals` - Search HubSpot deals

- `GET /docs` - Swagger UI documentation- `search_calendar` - Search calendar events

- `GET /redoc` - ReDoc documentation

### CRM Tools

## Background Worker- `get_contact_by_id` - Get detailed contact info

- `update_contact` - Update contact properties

The background worker processes asynchronous tasks:- `create_note` - Add note to contact

- `get_contact_notes` - Retrieve contact notes

```bash

# Start worker (in development)### Memory Tools

python -m app.services.tasks_worker- `create_memory_rule` - Create persistent AI instruction

- `list_memory_rules` - View all memory rules

# Worker handles:

- Email synchronization from GmailAll tools are defined in `app/services/tools.py` with OpenAI function calling schema.

- Calendar event synchronization

- LLM-based event processing## Vector Search (RAG)

- Memory rule evaluation

- Document embedding generationThe system uses **pgvector** for semantic search:

```

1. **Embedding Generation**

## OAuth Setup   - All emails and contacts are embedded using OpenAI `text-embedding-3-small`

   - Embeddings stored in `vectoritem` table

### Google Cloud Platform   - Automatic chunking for long content



1. Create a project in Google Cloud Console2. **Retrieval**

2. Enable Gmail API and Google Calendar API   - Cosine similarity search

3. Create OAuth 2.0 credentials   - Configurable top-k results

4. Add authorized redirect URIs:   - Metadata filtering by user and type

   - Development: `http://localhost:8000/api/auth/google/callback`

   - Production: `https://your-domain.com/api/auth/google/callback`3. **Augmented Generation**

5. Configure OAuth consent screen   - Retrieved context injected into AI prompts

6. Add required scopes:   - Source citations in responses

   - `https://www.googleapis.com/auth/gmail.modify`   - Relevance scoring

   - `https://www.googleapis.com/auth/calendar`

   - `https://www.googleapis.com/auth/userinfo.email`Implementation in `app/services/rag.py`

   - `https://www.googleapis.com/auth/userinfo.profile`

## Security Features

### HubSpot

- **OAuth 2.0** with PKCE for secure authentication

1. Create a HubSpot developer account- **httpOnly cookies** for session management

2. Create a new app- **Refresh token rotation** every 7 days

3. Configure OAuth settings- **Rate limiting** - 100 requests/minute per IP

4. Add scopes:- **PII redaction** in logs (emails, names, tokens)

   - `crm.objects.contacts.read`- **SQL injection protection** via SQLAlchemy ORM

   - `crm.objects.contacts.write`- **CORS** - Configured for frontend origin

   - `crm.objects.deals.read`- **Input validation** using Pydantic models

   - `crm.objects.deals.write`

5. Add redirect URI: `http://localhost:8000/api/auth/hubspot/callback`## Logging & Observability



Detailed instructions: See `OAUTH_SETUP.md`- **Structured JSON logging** for production

- **Request tracing** with correlation IDs

## Testing- **PII redaction filter** automatically removes sensitive data

- **Performance metrics** for database queries

```bash- **Error tracking** with full stack traces

# Run tests

pytestConfigure log level via `LOG_LEVEL` environment variable.



# Run with coverage## Testing

pytest --cov=app

```bash

# Run specific test file# Run all tests

pytest tests/test_api.pypytest



# Run with verbose output# Run with coverage

pytest -vpytest --cov=app --cov-report=html

```

# Run specific test file

## Production Deploymentpytest tests/test_chat.py



### Docker Build# Run with verbose output

pytest -v

```bash```

# Build production image

docker build -t financial-advisor-backend:latest .## 🐛 Troubleshooting



# Run container### Database Connection Issues

docker run -p 8000:8000 --env-file .env financial-advisor-backend:latest

``````bash

# Check PostgreSQL is running

### Fly.io Deploymentdocker-compose ps db



```bash# View database logs

# Install Fly CLIdocker-compose logs db

curl -L https://fly.io/install.sh | sh

# Connect to database

# Login to Fly.iodocker exec -it financial-advisor-db psql -U postgres -d financial_advisor

fly auth login

# Reset database

# Create appdocker-compose down -v

fly apps create financial-advisor-backenddocker-compose up -d

alembic upgrade head

# Set secrets```

fly secrets set OPENAI_API_KEY=sk-...

fly secrets set GOOGLE_CLIENT_SECRET=...### OAuth Errors

fly secrets set HUBSPOT_CLIENT_SECRET=...

fly secrets set SECRET_KEY=...- Verify redirect URIs match exactly in Google Cloud Console

- Check OAuth credentials in `.env`

# Deploy- Ensure APIs are enabled (Gmail, Calendar, People)

fly deploy- Clear browser cookies and try again



# View logs### Import Errors

fly logs

``````bash

# Verify Python version

## Performance Optimizationpython --version  # Should be 3.13+



- Database connection pooling configured for production# Reinstall dependencies

- Background worker separates heavy operations from API requestspip install -r requirements.txt --upgrade

- Vector search optimized with pgvector indexes

- Redis caching for frequently accessed data (optional)# Check virtual environment is activated

- Rate limiting prevents API abusewhich python

```

## Security Best Practices

### Worker Not Processing Tasks

- Never commit `.env` file to version control

- Use strong SECRET_KEY (minimum 32 characters)```bash

- Rotate OAuth credentials regularly# Check worker logs

- Keep dependencies updateddocker-compose logs worker

- Enable CORS only for trusted origins

- Use HTTPS in production# Manually check tasks table

- Implement rate limiting on all endpointsdocker exec -it financial-advisor-db psql -U postgres -d financial_advisor -c "SELECT status, COUNT(*) FROM task GROUP BY status;"



## Monitoring# Restart worker

docker-compose restart worker

- Health check endpoint at `/health````

- Structured logging with correlation IDs

- Error tracking with stack traces## 📚 Project Structure

- Performance metrics collection

- Database query logging (development only)```

backend/

## Troubleshooting├── app/

│   ├── api/                    # API route handlers

### Common Issues│   │   ├── auth_google.py     # Google OAuth

│   │   ├── auth_hubspot.py    # HubSpot OAuth

**Database connection fails:**│   │   ├── chat.py            # Chat streaming

```bash│   │   ├── rules.py           # Memory rules

# Check PostgreSQL is running│   │   ├── embeddings.py      # Vector search

docker compose ps db│   │   └── ...

│   ├── core/                  # Core configuration

# Verify DATABASE_URL is correct│   │   ├── config.py          # Settings and environment

echo $DATABASE_URL│   │   ├── database.py        # Database connection

```│   │   ├── security.py        # Security utilities

│   │   ├── observability.py   # Logging setup

**OAuth redirect fails:**│   │   └── rate_limiting.py   # Rate limiter

```bash│   ├── models/                # SQLAlchemy models

# Ensure redirect URI matches exactly in:│   │   ├── base.py           # Base model class

# 1. .env file│   │   ├── user.py           # User model

# 2. Google Cloud Console│   │   ├── contact.py        # Contact model

# 3. HubSpot app settings│   │   ├── email.py          # Email model

```│   │   ├── vector_item.py    # Embedding model

│   │   ├── memory_rule.py    # Memory rule model

**Worker not processing tasks:**│   │   └── task.py           # Background task model

```bash│   ├── services/              # Business logic

# Check worker logs│   │   ├── tools.py          # AI function tools

docker compose logs -f worker│   │   ├── rag.py            # Vector search/RAG

│   │   ├── openai_prompts.py # AI prompt templates

# Verify DATABASE_URL and OPENAI_API_KEY│   │   ├── gmail_sync.py     # Gmail integration

```│   │   ├── calendar_sync.py  # Calendar integration

│   │   ├── hubspot_sync.py   # HubSpot integration

**pgvector extension not found:**│   │   ├── embeddings.py     # Embedding generation

```bash│   │   ├── embedding_pipeline.py  # Batch embedding

# Install extension manually│   │   ├── memory_rules.py   # Memory rule logic

docker compose exec db psql -U postgres -d financial_advisor -c "CREATE EXTENSION vector;"│   │   └── tasks_worker.py   # Background worker

```│   ├── utils/                 # Utilities

│   │   ├── oauth_helpers.py  # OAuth utilities

## Contributing│   │   ├── security.py       # Security helpers

│   │   └── chunking.py       # Text chunking

1. Follow PEP 8 style guide│   └── main.py               # FastAPI application

2. Add type hints to all functions├── migrations/                # Alembic migrations

3. Write docstrings for public APIs│   └── versions/             # Migration scripts

4. Add tests for new features├── tests/                    # Test files

5. Update documentation├── .env.example             # Environment template

├── alembic.ini              # Alembic configuration

## License├── docker-compose.yml       # Docker services

├── Dockerfile               # Backend container

Proprietary and confidential. Unauthorized copying or distribution is prohibited.├── requirements.txt         # Python dependencies

├── OAUTH_SETUP.md          # OAuth setup guide
└── README.md               # This file
```

## 🚀 Deployment

### Docker Production Build

```bash
# Build image
docker build -t financial-advisor-backend:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  --env-file .env.production \
  --name financial-advisor-backend \
  financial-advisor-backend:latest
```

### Production Considerations

1. **Environment Variables**
   - Use production OAuth redirect URIs
   - Generate secure SECRET_KEY (32+ characters)
   - Set `ENVIRONMENT=production`
   - Configure proper CORS origins

2. **Database**
   - Use managed PostgreSQL service
   - Enable SSL connections
   - Set up automated backups
   - Configure connection pooling

3. **Security**
   - Enable HTTPS only
   - Configure rate limiting appropriately
   - Set up WAF (Web Application Firewall)
   - Regular security audits

4. **Monitoring**
   - Set up log aggregation (e.g., ELK stack)
   - Configure error tracking (e.g., Sentry)
   - Monitor API performance
   - Set up alerts for failures

5. **Scaling**
   - Use load balancer for multiple instances
   - Scale worker processes independently
   - Configure Redis for session storage (optional)
   - Implement caching layer

## 📖 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [pgvector Guide](https://github.com/pgvector/pgvector)
- [Google OAuth Documentation](https://developers.google.com/identity/protocols/oauth2)
- [HubSpot API Documentation](https://developers.hubspot.com/docs/api/overview)

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Add/update tests
4. Run linting: `ruff check .`
5. Run tests: `pytest`
6. Submit pull request

## 📝 License

This project is private and proprietary.

---

**Built with FastAPI, PostgreSQL, and OpenAI** 🚀
- **Graceful shutdown** on SIGINT/SIGTERM signals
- **Orphaned task recovery** on startup (reclaims tasks locked > 5 minutes)
- **Database row-level locking** for safe multi-worker deployment

### Task Lifecycle

1. **pending** → Task created, waiting for worker
2. **in_progress** → Worker acquired task, executing
3. **done** → Task completed successfully
4. **failed** → Task failed after max retry attempts

### Configuration

Environment variables:
- `WORKER_POLL_INTERVAL`: Seconds between polling cycles (default: 5)
- `WORKER_MAX_CONCURRENT`: Max concurrent tasks per worker (default: 10)
- `WORKER_LOCK_TIMEOUT`: Seconds before task is considered orphaned (default: 300)

## Webhooks

The application supports webhook integrations for real-time event processing from external services.

### Supported Webhooks

**HubSpot** - `POST /api/webhooks/hubspot`
- Contact creation, updates, deletion
- Deal property changes
- Requires signature verification (HMAC-SHA256)

**Gmail** - `POST /api/webhooks/gmail`
- New email notifications via Google Pub/Sub
- Email modifications
- Requires Pub/Sub topic configuration

**Google Calendar** - `POST /api/webhooks/calendar`
- Event creation, updates, deletion
- Requires Calendar API watch() setup
- Handles sync messages

### Memory Rules Engine

Users can define rules to automatically respond to events:

**Rule Syntax:**
```
when {event_type} then {action} [params]
```

**Examples:**
- `when hubspot.contact.creation then create_task type=welcome_email priority=high`
- `when gmail.message.received then log`

**Supported Actions:**
- `create_task`: Create async task for worker
- `log`: Log event for debugging

### Webhook Security

- **Signature Verification**: HubSpot webhooks validated with HMAC-SHA256
- **Replay Protection**: In-memory deduplication (use Redis in production)
- **Input Validation**: Strict payload validation with error handling
- **Rate Limiting**: Protects against webhook floods

### Setup Instructions

1. **HubSpot**: Configure webhook URL in HubSpot Developer Portal
2. **Gmail**: Set up Google Pub/Sub push subscription pointing to `/api/webhooks/gmail`
3. **Calendar**: Call Calendar API `watch()` method with callback URL `/api/webhooks/calendar`

## Security

The application implements comprehensive security measures:

- **Security Headers**: CSP, X-Frame-Options, X-Content-Type-Options, etc.
- **PII Redaction**: Automatic redaction of sensitive data from logs
- **Input Sanitization**: HTML sanitization, SQL injection detection, XSS prevention
- **Rate Limiting**: Per-user and global rate limits for APIs and OpenAI
- **OAuth Security**: CSRF protection with state parameter, secure token storage
- **Webhook Security**: Signature verification, replay protection

See [SECURITY.md](SECURITY.md) for detailed security documentation.

## Observability

The application provides comprehensive monitoring and logging:

### Health Checks

- `GET /health` - Liveness check
- `GET /ready` - Readiness check (includes database connectivity)
- `GET /health/database` - Detailed database health

### Metrics

Prometheus metrics available at `/metrics` (requires `prometheus-client` installed):

- HTTP request metrics (rate, duration, in-progress)
- OpenAI API metrics (requests, tokens, latency)
- RAG search metrics
- Task queue metrics
- Webhook event metrics

### Structured Logging

All logs output in JSON format with:
- ISO 8601 timestamps
- Correlation IDs for request tracking
- Automatic PII redaction
- Exception stack traces
- Custom contextual fields

### Monitoring Setup

See [OBSERVABILITY.md](OBSERVABILITY.md) for detailed instructions on:
- Prometheus + Grafana setup
- Sentry error tracking
- Log aggregation (Datadog, CloudWatch, Loki)
- Alerting rules

## Development

### Prerequisites

- Python 3.11+
- PostgreSQL with pgvector extension
- Redis (optional, for production rate limiting)

### Local Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Run database migrations:
   ```bash
   alembic upgrade head
   ```

4. Start development server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_chat.py
```

### Code Quality

```bash
# Type checking
mypy app/

# Linting
ruff check app/

# Formatting
black app/
```

## Deployment

### Fly.io (Recommended)

1. Install Fly CLI:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. Create app:
   ```bash
   fly launch
   ```

3. Set secrets:
   ```bash
   fly secrets set OPENAI_API_KEY=xxx
   fly secrets set GOOGLE_CLIENT_ID=xxx
   fly secrets set GOOGLE_CLIENT_SECRET=xxx
   fly secrets set HUBSPOT_CLIENT_ID=xxx
   fly secrets set HUBSPOT_CLIENT_SECRET=xxx
   fly secrets set SECRET_KEY=xxx
   ```

4. Deploy:
   ```bash
   fly deploy
   ```

See [deployment guide](docs/deployment.md) for more details.

## Project Structure

```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   ├── auth_google.py
│   │   ├── auth_hubspot.py
│   │   ├── chat.py
│   │   ├── embeddings.py
│   │   ├── health.py
│   │   ├── ingest.py
│   │   └── webhooks.py
│   ├── core/             # Core utilities
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logging_config.py
│   │   ├── observability.py
│   │   ├── rate_limiting.py
│   │   └── security.py
│   ├── models/           # Database models
│   │   ├── contact.py
│   │   ├── email.py
│   │   ├── memory_rule.py
│   │   ├── task.py
│   │   ├── user.py
│   │   └── vector_item.py
│   ├── services/         # Business logic
│   │   ├── embeddings.py
│   │   ├── embedding_pipeline.py
│   │   ├── gmail_sync.py
│   │   ├── hubspot_sync.py
│   │   ├── memory_rules.py
│   │   ├── openai_prompts.py
│   │   ├── rag.py
│   │   ├── tasks_worker.py
│   │   ├── text_chunker.py
│   │   └── tools.py
│   ├── utils/            # Shared utilities
│   │   ├── oauth_helpers.py
│   │   └── security.py
│   └── main.py           # Application entry point
├── migrations/           # Alembic migrations
├── Dockerfile
├── requirements.txt
└── README.md
```

## Documentation

- [Security Guide](SECURITY.md) - Security measures and best practices
- [Observability Guide](OBSERVABILITY.md) - Monitoring, logging, and metrics
- [OAuth Setup](OAUTH_SETUP.md) - OAuth configuration for Google and HubSpot

## License

[Your License Here]

