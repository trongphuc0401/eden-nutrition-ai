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

## OpenAI structured output test

This branch adds a small OpenAI service that returns a structured smoothie plan.

Run the dry check without an API key:

```bash
python scripts/test_openai_structured_output.py
```

To make a live OpenAI call, set these values in `.env`:

```txt
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Then run the same script again.
