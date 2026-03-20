# Design Document -- AI Customer Support Insight Platform

## 1. Architecture Overview

```
                         +-------------------+
                         |   React 18 SPA    |
                         |  MUI + Recharts   |
                         +--------+----------+
                                  |
                           HTTP / REST
                                  |
                         +--------v----------+
                         |    FastAPI App     |
                         |  (backend/main.py) |
                         +---+----+----+-----+
                             |    |    |
               +-------------+    |    +-------------+
               |                  |                  |
      +--------v------+  +-------v--------+  +------v--------+
      | Pipeline       |  | AI Engine      |  | Data Layer    |
      | ingest > clean |  | llm.py         |  | SQLAlchemy    |
      | > enrich >     |  | embeddings.py  |  | SQLite DB     |
      | store          |  | classical.py   |  | ChromaDB      |
      +----------------+  +-------+--------+  +---------------+
                                  |
                    +-------------+-------------+
                    |                           |
           +--------v-------+         +--------v--------+
           | Groq API       |         | OpenAI API      |
           | Llama 3.3 70B  |         | Embeddings      |
           +----------------+         +-----------------+
```

## 2. AI Approach

### Why Groq Llama 3.3 70B

Groq provides free-tier access to Llama 3.3 70B with sub-second latency through their LPU inference engine. This gives us a production-quality 70B-parameter model at zero cost for moderate throughput (30 RPM free tier). The model handles three tasks via structured JSON prompts:

- **Zero-shot classification** -- categorize tickets into 8 categories without training data
- **Sentiment + frustration analysis** -- extract sentiment label, frustration score (0-1), and reasoning
- **Response generation** -- produce empathetic 2-3 sentence agent replies with RAG context

### Why OpenAI Embeddings + ChromaDB

OpenAI text-embedding-3-small produces 1536-dimensional vectors optimized for semantic similarity. ChromaDB stores these locally with HNSW indexing (cosine distance) for sub-millisecond retrieval. Together they enable RAG: when generating a response, we retrieve the 3 most similar resolved tickets and inject their resolutions as context for the LLM.

### Why TF-IDF + TextBlob Fallback

When no API keys are configured, the system must still function. The classical pipeline uses:

- **Keyword frequency scoring** -- match ticket text against category keyword lists, score by hit count
- **TextBlob polarity** -- rule-based sentiment from the Pattern library
- **Frustration keywords** -- curated list of 16 frustration indicators with additive scoring
- **Template responses** -- pre-written responses per category

This ensures the platform is fully demonstrable without any external API dependencies.

## 3. Data Model

### Tickets Table

| Column | Type | Description |
|---|---|---|
| id | Integer PK | Auto-increment |
| ticket_id | String UNIQUE | Original or generated ticket ID |
| timestamp | DateTime | Ticket creation time |
| customer_id | String | Hashed customer identifier |
| channel | String | email, chat, phone, social media |
| message | Text | Customer message body |
| agent_reply | Text | Original agent response (if available) |
| product | String | Product name |
| order_value | Float | Order dollar amount |
| customer_country | String | 2-letter country code |
| resolution_status | String | open, closed, pending |
| ai_category | String | LLM/TF-IDF assigned category |
| ai_sentiment | String | positive, neutral, negative |
| ai_frustration | Float | 0.0-1.0 frustration score |
| ai_response | Text | AI-generated suggested response |
| ai_confidence | Float | 0.0-1.0 classification confidence |
| processed_at | DateTime | When AI enrichment completed |

### Insights Table

| Column | Type | Description |
|---|---|---|
| id | Integer PK | Auto-increment |
| insight_type | String | top_issue, anomaly, trend |
| category | String | Related ticket category |
| metric_value | Float | Count, percentage, or spike value |
| description | Text | Human-readable insight text |
| metadata_json | Text | JSON with detailed metrics |
| created_at | DateTime | Insight generation timestamp |

## 4. Data Pipeline Stages

```
CSV Upload / Synthetic Gen
        |
        v
  [1] INGEST -- Load CSV, detect schema (Kaggle or custom), map columns,
                hash customer names, generate order values
        |
        v
  [2] CLEAN  -- Deduplicate by ticket_id, fill nulls, parse timestamps,
                filter messages < 10 chars, normalize text fields
        |
        v
  [3] ENRICH -- For each ticket:
                (a) Categorize via LLM or TF-IDF
                (b) Analyze sentiment + frustration
                (c) Find similar tickets via ChromaDB vector search
                (d) Generate response with RAG context
                (e) Store embedding in ChromaDB
        |
        v
  [4] STORE  -- Upsert tickets to SQLite via SQLAlchemy
                Generate insights: top issues by category,
                anomaly detection (mean + 2-sigma on daily counts)
```

The pipeline runs in a background thread with progress tracking exposed via `GET /api/pipeline/status`. The frontend polls this endpoint to show real-time progress bars.

## 5. Scalability Path

| Current State | Production Target | Migration Path |
|---|---|---|
| SQLite | PostgreSQL | Change DATABASE_URL, add connection pooling |
| Background thread | Celery + Redis | Extract _run_pipeline into Celery task |
| Synchronous enrichment | Async batch processing | Batch Groq API calls, parallel embedding generation |
| In-memory pipeline state | Redis-backed state | Store PipelineStatus in Redis |
| Single process | Gunicorn workers | Add gunicorn with 4-8 uvicorn workers |
| Local ChromaDB | Managed Pinecone/Weaviate | Swap embeddings.py client |
| TF-IDF keyword matching | Fine-tuned classifier | Train on labeled ticket data |
| 500-ticket sample cap | Full dataset processing | Remove sample_size, add pagination to enrichment |

## 6. Key Tradeoffs

| Decision | Chosen | Alternative | Rationale |
|---|---|---|---|
| LLM provider | Groq (free tier) | OpenAI GPT-4o | Zero cost, sub-second latency, 70B quality |
| Embedding model | OpenAI text-embedding-3-small | Local sentence-transformers | Better accuracy per dimension, low cost ($0.02/1M tokens) |
| Vector DB | ChromaDB (local) | Pinecone, Weaviate | Zero infrastructure, persistent storage, good enough for < 100K vectors |
| Database | SQLite | PostgreSQL | Zero setup, sufficient for single-user demo, easy migration path |
| Pipeline execution | Background thread | Celery | No Redis dependency, adequate for single-server |
| Frontend framework | React 18 + MUI | Next.js | SPA is sufficient, no SSR needed for dashboard |
| Fallback ML | TextBlob + keywords | spaCy, Hugging Face | Minimal dependencies, no model downloads, instant startup |
| Anomaly detection | Mean + 2-sigma | Isolation Forest, DBSCAN | Simple, interpretable, no training required |
| Deployment | Docker single-stage | Kubernetes | Appropriate for demo/MVP scale |

## 7. Security Considerations

- Customer names are hashed (MD5) on ingestion to avoid storing PII
- API keys are loaded from environment variables, never committed
- CORS is restricted to localhost development origins
- File upload is limited to CSV format with a 50,000 row cap
- No authentication layer (demo scope) -- production would add OAuth2/JWT

## 8. Monitoring

- Health check endpoint: `GET /api/mode` returns AI engine status
- Pipeline status: `GET /api/pipeline/status` returns state, progress, errors
- Docker health check pings `/api/mode` every 30 seconds
- GitHub Actions CI validates imports, frontend build, and Docker build on every push
