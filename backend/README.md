# FastAPI Backend Skeleton

## Getting Started

1. Create a virtual environment with Python 3.11 or higher and activate it.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and update the values for your environment.
4. Start the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Database Setup and Alembic Migrations

1. Ensure PostgreSQL is running and the database defined in `DATABASE_URL` is accessible.
2. The project uses SQLModel models and Alembic for migrations.
3. Initialize Alembic (run from the `backend/` directory):
   ```bash
   alembic init migrations
   ```
4. Update `alembic.ini` with your `DATABASE_URL` and edit `migrations/env.py` to import `SQLModel.metadata`.
5. Generate a migration:
   ```bash
   alembic revision --autogenerate -m "create tables"
   ```
6. Apply migrations:
   ```bash
   alembic upgrade head
   ```
7. The database startup hook in `app/main.py` will ensure tables exist and the `pgvector` extension is created when possible.

## Background Worker

The application includes a background worker for processing asynchronous tasks (emails, calendar events, contact creation, etc.).

### Running the Worker

Start the worker process:
```bash
python -m app.services.tasks_worker
```

### Worker Features

- **Polling-based task processing** with configurable interval (default: 5 seconds)
- **Concurrency control** using `SELECT FOR UPDATE SKIP LOCKED` (max 10 concurrent tasks)
- **Exponential backoff retry** with configurable max attempts (default: 3)
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

