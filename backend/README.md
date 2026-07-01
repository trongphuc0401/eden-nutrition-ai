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

Current backend endpoints:

```txt
GET  /health
GET  /system-status
POST /profiles/analyze
POST /knowledge/search-preview
POST /smoothies/generate
POST /smoothies/evaluate
POST /smoothies/generate-and-evaluate
GET  /research-rules/preview
```

`/system-status` returns a readiness dashboard for P2/P3 capabilities:

```txt
openai_generation, database_persistence, vector_search,
local_knowledge_fallback, research_rules, guardrail_and_evaluation
```

Each capability includes `status`, `ready`, `reason`, and an optional `next_action`.

`/smoothies/generate` supports query params:

```txt
use_rag=true|false
knowledge_limit=1..10
persist_result=true|false
```

`/smoothies/evaluate` accepts this request body:

```txt
{ "profile": ProfileInput, "plan": SmoothiePlanResponse }
```

Research scope:

```txt
ProfileInput requires age >= 18.
Smoothie generation is limited to profiles with BMI >= 25.
Use /profiles/analyze to inspect BMI and scope classification before generation.
```

Bootstrap database tables when PostgreSQL is available:

```bash
python scripts/init_db.py
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

Run the backend API flow test without starting `uvicorn`:

```bash
python scripts/test_nutrition_api_flow.py
```

Run prompt and guardrail verification:

```bash
python scripts/test_guardrail_and_prompt.py
```

Run smoothie evaluation verification:

```bash
python scripts/test_evaluation_flow.py
python scripts/test_evaluation_edge_cases.py
```

Evaluation responses include an `evaluation_report` summary with:

```txt
score, decision, data_coverage, issues, recommendations
```

Run the combined readiness and generate/evaluate API verification:

```bash
python scripts/test_openapi_contract.py
python scripts/test_generate_and_evaluate_api.py
```

Recommended P2/P3 verification set while P1 data is still incomplete:

```bash
python scripts/test_p2_p3_smoke.py
```

The smoke runner executes these checks in order:

```txt
compileall
test_openapi_contract.py
test_guardrail_and_prompt.py
test_evaluation_edge_cases.py
test_generate_and_evaluate_api.py
```

Run checks individually when debugging:

```bash
python -m compileall app scripts
python scripts/test_openapi_contract.py
python scripts/test_guardrail_and_prompt.py
python scripts/test_evaluation_edge_cases.py
python scripts/test_generate_and_evaluate_api.py
```

Import fallback research rules:

```bash
python scripts/import_research_rules.py --dry-run
python scripts/import_research_rules.py
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

## Import Vietnamese fruit seed data

This project includes a full-data seed file from the `Fruit_Data` Google Sheet:

```txt
backend/data/vietnamese_fruits_seed.json
```

The seed preserves every exported source column in `raw_columns` and `raw_values`. Normalized fields such as `ingredient_name`, `season_months`, and `nutrition_per_100g` are added only to make search and import easier.

Rebuild the seed from the raw CSV export:

```bash
python scripts/build_vietnamese_fruit_seed.py
```

Preview the seed file without writing to PostgreSQL:

```bash
python scripts/import_vietnamese_fruit_data.py --dry-run
```

Import records into `nutrition_knowledge` without embeddings:

```bash
python scripts/import_vietnamese_fruit_data.py
```

Import records and create OpenAI embeddings:

```bash
python scripts/import_vietnamese_fruit_data.py --embed
```
