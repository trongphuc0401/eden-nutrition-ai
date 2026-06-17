# AI Nutrition Coach Backend

FastAPI backend for the AI Nutrition Coach project.

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy the environment example:

```bash
copy .env.example .env
```

## Run locally

Start the development server from the `backend` folder:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```txt
http://127.0.0.1:8000
```

## Health check

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Database configuration

This branch adds SQLAlchemy models and a PostgreSQL connection setting only. It does not create database migrations yet.

Set `DATABASE_URL` in `.env`:

```txt
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_nutrition
```
