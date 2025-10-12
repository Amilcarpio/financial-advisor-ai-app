# Financial Advisor AI - Backend

FastAPI-based backend with AI chat capabilities, CRM integrations, and vector search.

## Quick Start

### Using Docker (Recommended)

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your API keys and credentials

# Start all services (PostgreSQL + Backend)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

Backend will be available at `http://localhost:8000`
API documentation at `http://localhost:8000/docs`

### Local Development (Without Docker)

1. **Install Python 3.13+** and create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup PostgreSQL with pgvector:**
   ```bash
   # Install PostgreSQL and pgvector extension
   # On macOS with Homebrew:
   brew install postgresql pgvector
   
   # Create database
   createdb financial_advisor
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start development server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## Prerequisites

- Python 3.13+
- PostgreSQL 14+ with pgvector extension
- Docker & Docker Compose (for containerized deployment)
- OpenAI API key
- Google OAuth credentials
- HubSpot API credentials (optional)

## Configuration

### Required Environment Variables

```bash
# API Keys
OPENAI_API_KEY=sk-...

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/financial_advisor

# Security
SECRET_KEY=your-secret-key-minimum-32-characters
FRONTEND_URL=http://localhost:5173

# Optional: HubSpot Integration
HUBSPOT_CLIENT_ID=your-hubspot-client-id
HUBSPOT_CLIENT_SECRET=your-hubspot-secret
HUBSPOT_REDIRECT_URI=http://localhost:8000/api/auth/hubspot/callback
```

See `.env.example` for all available configuration options.

### OAuth Setup

See [OAUTH_SETUP.md](OAUTH_SETUP.md) for detailed instructions on:
- Creating Google Cloud project
- Enabling Gmail and Calendar APIs
- Setting up HubSpot OAuth
- Configuring redirect URIs

## Database Setup

The project uses **SQLAlchemy** with **PostgreSQL** and **pgvector** for vector search.

### Migrations with Alembic

```bash
# Generate a new migration after model changes
alembic revision --autogenerate -m "description of changes"

# Apply all pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history
```

### Database Schema

Key models:
- **User** - User accounts with OAuth tokens
- **Contact** - HubSpot contacts
- **Email** - Gmail messages with metadata
- **VectorItem** - Embedded content for semantic search
- **MemoryRule** - Persistent AI instructions
- **Task** - Asynchronous background tasks

## Background Worker

The application includes a background worker for processing asynchronous tasks.

### Running the Worker

```bash
# With Docker (already running in docker-compose)
docker-compose logs -f worker

# Locally
python -m app.services.tasks_worker
```

### Worker Features

- **Polling-based task processing** - Checks for new tasks every 5 seconds
- **Concurrency control** - Max 10 concurrent tasks using `SELECT FOR UPDATE SKIP LOCKED`
- **Exponential backoff retry** - Up to 3 attempts with increasing delays
- **Task types:**
  - Email sync from Gmail
  - Calendar event sync
  - Contact creation/updates
  - Embedding generation
  - HubSpot data sync

### Task Monitoring

```bash
# Check task status in database
docker exec -it financial-advisor-db psql -U postgres -d financial_advisor -c "SELECT * FROM task ORDER BY created_at DESC LIMIT 10;"
```

## API Endpoints

### Authentication
- `GET /api/auth/google/start` - Initiate Google OAuth flow
- `GET /api/auth/google/callback` - Google OAuth callback
- `GET /api/auth/hubspot/start` - Initiate HubSpot OAuth flow
- `GET /api/auth/hubspot/callback` - HubSpot OAuth callback
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout user

### Chat
- `POST /api/chat/stream` - Stream chat responses with function calling

### Memory Rules
- `GET /api/rules` - List all memory rules
- `POST /api/rules` - Create new memory rule
- `GET /api/rules/{id}` - Get specific rule
- `PUT /api/rules/{id}` - Update rule
- `DELETE /api/rules/{id}` - Delete rule

### Embeddings & RAG
- `POST /api/ingest/emails` - Manually trigger email ingestion
- `POST /api/ingest/contacts` - Manually trigger contact ingestion
- `POST /api/embeddings/search` - Search embedded content

### Health
- `GET /api/health` - Health check endpoint
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

## AI Function Tools

The AI can execute these functions during conversation:

### Search Tools
- `search_emails` - Semantic search across all emails
- `search_contacts` - Search HubSpot contacts
- `search_deals` - Search HubSpot deals
- `search_calendar` - Search calendar events

### CRM Tools
- `get_contact_by_id` - Get detailed contact info
- `update_contact` - Update contact properties
- `create_note` - Add note to contact
- `get_contact_notes` - Retrieve contact notes

### Memory Tools
- `create_memory_rule` - Create persistent AI instruction
- `list_memory_rules` - View all memory rules

All tools are defined in `app/services/tools.py` with OpenAI function calling schema.

## Vector Search (RAG)

The system uses **pgvector** for semantic search:

1. **Embedding Generation**
   - All emails and contacts are embedded using OpenAI `text-embedding-3-small`
   - Embeddings stored in `vectoritem` table
   - Automatic chunking for long content

2. **Retrieval**
   - Cosine similarity search
   - Configurable top-k results
   - Metadata filtering by user and type

3. **Augmented Generation**
   - Retrieved context injected into AI prompts
   - Source citations in responses
   - Relevance scoring

Implementation in `app/services/rag.py`

## Security Features

- **OAuth 2.0** with PKCE for secure authentication
- **httpOnly cookies** for session management
- **Refresh token rotation** every 7 days
- **Rate limiting** - 100 requests/minute per IP
- **PII redaction** in logs (emails, names, tokens)
- **SQL injection protection** via SQLAlchemy ORM
- **CORS** - Configured for frontend origin
- **Input validation** using Pydantic models

## Logging & Observability

- **Structured JSON logging** for production
- **Request tracing** with correlation IDs
- **PII redaction filter** automatically removes sensitive data
- **Performance metrics** for database queries
- **Error tracking** with full stack traces

Configure log level via `LOG_LEVEL` environment variable.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_chat.py

# Run with verbose output
pytest -v
```

## 🐛 Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps db

# View database logs
docker-compose logs db

# Connect to database
docker exec -it financial-advisor-db psql -U postgres -d financial_advisor

# Reset database
docker-compose down -v
docker-compose up -d
alembic upgrade head
```

### OAuth Errors

- Verify redirect URIs match exactly in Google Cloud Console
- Check OAuth credentials in `.env`
- Ensure APIs are enabled (Gmail, Calendar, People)
- Clear browser cookies and try again

### Import Errors

```bash
# Verify Python version
python --version  # Should be 3.13+

# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Check virtual environment is activated
which python
```

### Worker Not Processing Tasks

```bash
# Check worker logs
docker-compose logs worker

# Manually check tasks table
docker exec -it financial-advisor-db psql -U postgres -d financial_advisor -c "SELECT status, COUNT(*) FROM task GROUP BY status;"

# Restart worker
docker-compose restart worker
```

## 📚 Project Structure

```
backend/
├── app/
│   ├── api/                    # API route handlers
│   │   ├── auth_google.py     # Google OAuth
│   │   ├── auth_hubspot.py    # HubSpot OAuth
│   │   ├── chat.py            # Chat streaming
│   │   ├── rules.py           # Memory rules
│   │   ├── embeddings.py      # Vector search
│   │   └── ...
│   ├── core/                  # Core configuration
│   │   ├── config.py          # Settings and environment
│   │   ├── database.py        # Database connection
│   │   ├── security.py        # Security utilities
│   │   ├── observability.py   # Logging setup
│   │   └── rate_limiting.py   # Rate limiter
│   ├── models/                # SQLAlchemy models
│   │   ├── base.py           # Base model class
│   │   ├── user.py           # User model
│   │   ├── contact.py        # Contact model
│   │   ├── email.py          # Email model
│   │   ├── vector_item.py    # Embedding model
│   │   ├── memory_rule.py    # Memory rule model
│   │   └── task.py           # Background task model
│   ├── services/              # Business logic
│   │   ├── tools.py          # AI function tools
│   │   ├── rag.py            # Vector search/RAG
│   │   ├── openai_prompts.py # AI prompt templates
│   │   ├── gmail_sync.py     # Gmail integration
│   │   ├── calendar_sync.py  # Calendar integration
│   │   ├── hubspot_sync.py   # HubSpot integration
│   │   ├── embeddings.py     # Embedding generation
│   │   ├── embedding_pipeline.py  # Batch embedding
│   │   ├── memory_rules.py   # Memory rule logic
│   │   └── tasks_worker.py   # Background worker
│   ├── utils/                 # Utilities
│   │   ├── oauth_helpers.py  # OAuth utilities
│   │   ├── security.py       # Security helpers
│   │   └── chunking.py       # Text chunking
│   └── main.py               # FastAPI application
├── migrations/                # Alembic migrations
│   └── versions/             # Migration scripts
├── tests/                    # Test files
├── .env.example             # Environment template
├── alembic.ini              # Alembic configuration
├── docker-compose.yml       # Docker services
├── Dockerfile               # Backend container
├── requirements.txt         # Python dependencies
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

