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
GET  /frontend/bootstrap
POST /profiles/analyze
POST /knowledge/search-preview
POST /smoothies/generate
POST /smoothies/evaluate
POST /smoothies/generate-and-evaluate
GET  /research-rules/preview
```

`/system-status` returns a readiness dashboard for P2/P3 capabilities:

```txt
llm_generation, database_persistence, vector_search,
local_knowledge_fallback, research_rules, guardrail_and_evaluation
```

Each capability includes `status`, `ready`, `reason`, and an optional `next_action`.

The runtime also exposes the active provider names:

```txt
llm_provider, embedding_provider
```

Provider split:

| Use case | Recommended provider | Notes |
|---|---|---|
| Smoothie generation | `gemini`, `groq`, `cerebras`, `openrouter`, or `openai` | Pick one `LLM_PROVIDER` and matching `LLM_API_KEY`. |
| Embeddings for pgvector | `openai` or another OpenAI-compatible embedding provider | Gemini embeddings are not wired yet in this backend. |
| Free test driving | `gemini` for generation, local seed fallback for retrieval | Good for fast iteration without embedding setup. |

Vietnamese-first product rule:

```txt
Frontend/user-facing labels, sample profiles, reasons, safety warnings, and recommendations should be Vietnamese first.
Technical JSON field names stay English so the API contract remains stable.
```

Data storage split:

| Data type | Storage | Why |
|---|---|---|
| Nutrition knowledge and ingredient guidance | PostgreSQL table `nutrition_knowledge` plus pgvector column `embedding` | Used by RAG/vector search. |
| Nutrition thresholds | PostgreSQL table `nutrition_thresholds` | Used by automatic evaluation. |
| Allergy and clinical safety rules | PostgreSQL table `clinical_safety_rules` | Used by guardrails and safety checks. |
| Demo frontend profiles | `backend/data/demo_profiles_seed.json` and `/frontend/bootstrap` | UI samples only, not real user records. |
| Generated user profiles and smoothie plans | PostgreSQL tables `user_profiles` and `smoothie_plans` when `persist_result=true` | Runtime persistence for generated results. |

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

## LLM structured output test

This branch adds a small provider layer that returns a structured smoothie formula for Vietnamese adults with overweight or obesity.

Run the dry check without an API key:

```bash
python scripts/test_llm_structured_output.py
```

To make a live Gemini call, set these values in `.env`:

```txt
LLM_PROVIDER=gemini
LLM_API_KEY=your_gemini_key_here
LLM_MODEL=gemini-2.0-flash
```

Then run the same script again.

You can also switch to OpenAI-compatible providers such as Groq, Cerebras, or OpenRouter by changing `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, and optionally `LLM_BASE_URL`.

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
python scripts/test_frontend_bootstrap.py
python scripts/test_guardrail_and_prompt.py
python scripts/test_evaluation_edge_cases.py
python scripts/test_generate_and_evaluate_api.py
```

Import fallback research rules:

```bash
python scripts/import_research_rules.py --dry-run
python scripts/import_research_rules.py
```

Import Vietnamese demo data for frontend/RAG testing:

```bash
python scripts/import_demo_vi_data.py --dry-run
python scripts/import_demo_vi_data.py
```

This imports demo threshold rules, safety rules, and Vietnamese knowledge items. With `EMBEDDING_PROVIDER=gemini`, it also creates 1536-dimensional embeddings in PostgreSQL pgvector.

The graph runs:

```txt
START -> analyze_goal -> generate_smoothie_plan -> safety_check -> END
```

## RAG pgvector dry-run test

This branch adds pgvector support for `nutrition_knowledge.embedding`, configurable embedding providers, vector search, and prompt knowledge injection.

Run the dry-run without PostgreSQL or an OpenAI API key:

```bash
python scripts/test_rag_pgvector_dry_run.py
```

For real vector search later, PostgreSQL must have the `vector` extension enabled and `nutrition_knowledge.embedding` populated.

If you want to create embeddings during import, set an embeddings provider in `.env`:

```txt
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=your_key_here
EMBEDDING_MODEL=text-embedding-3-small
```

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

Import records and create embeddings:

```bash
python scripts/import_vietnamese_fruit_data.py --embed
```
