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

This branch adds a small OpenAI service that returns a structured smoothie formula for Vietnamese adults with overweight or obesity.

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

## LangGraph basic flow test

Run the basic nutrition graph:

```bash
python scripts/test_langgraph_flow.py
```

The graph runs:

```txt
START -> analyze_goal -> generate_smoothie_plan -> safety_check -> END
```

## RAG pgvector dry-run test

This branch adds pgvector support for `nutrition_knowledge.embedding`, OpenAI embedding creation, vector search, and prompt knowledge injection.

Run the dry-run without PostgreSQL or an OpenAI API key:

```bash
python scripts/test_rag_pgvector_dry_run.py
```

For real vector search later, PostgreSQL must have the `vector` extension enabled and `nutrition_knowledge.embedding` populated.

Vietnamese fruit origin constraints use these `nutrition_knowledge` metadata fields:

```txt
ingredient_name, category, origin_country, region, season_months, allowed_for_smoothie
```

By default, vector search can be constrained to fruits with Vietnamese origin and `allowed_for_smoothie=true`.
