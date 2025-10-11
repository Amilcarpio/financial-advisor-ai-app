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
