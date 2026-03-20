# Architecture -- AI Customer Support Insight Platform

## 1. System Architecture

```
+------------------------------------------------------------------+
|                        Client Browser                             |
|  +------------------------------------------------------------+  |
|  |  React 18 SPA  (Vite + MUI + Recharts)                     |  |
|  |  Pages: Upload | Dashboard | Tickets | Assistant | Analytics|  |
|  +-----------------------------+------------------------------+  |
+--------------------------------|----------------------------------+
                                 | HTTP (port 5173 dev / 8000 prod)
+--------------------------------v----------------------------------+
|                        FastAPI Server                             |
|  +------------------------------------------------------------+  |
|  |  backend/main.py                                            |  |
|  |  - REST endpoints (10 routes)                               |  |
|  |  - Pipeline orchestration (background thread)               |  |
|  |  - SPA static file serving (production)                     |  |
|  +------+-----------+-----------+-----------------------------+  |
|         |           |           |                                 |
|  +------v---+ +-----v-----+ +--v-----------+                     |
|  | Pipeline  | | AI Engine | | Data Layer   |                     |
|  | ingest.py | | llm.py    | | models.py    |                     |
|  | clean.py  | | embed.py  | | SQLAlchemy   |                     |
|  | enrich.py | | classic.  | | get_session()|                     |
|  | store.py  | | py        | |              |                     |
|  +----------+ +-----------+ +--------------+                     |
+------------------------------------------------------------------+
        |               |               |
        |        +------+------+        |
        |        |             |        |
   +----v---+ +-v--------+ +--v-----------+
   | ChromaDB| | Groq API | | SQLite DB    |
   | (local) | | (Llama   | | tickets      |
   | cosine  | |  3.3 70B)| | insights     |
   | HNSW    | +----------+ +--------------+
   +---------+ |          |
               | +-v------+---+
               | | OpenAI API |
               | | embed-3-   |
               | | small      |
               | +------------+
               |
     (fallback when no API keys)
               |
        +------v--------+
        | Classical ML  |
        | TF-IDF + keys |
        | TextBlob      |
        | Templates     |
        +---------------+
```

## 2. Component Details

| Component | File(s) | Responsibility | Dependencies |
|---|---|---|---|
| FastAPI App | backend/main.py | HTTP routing, CORS, pipeline lifecycle | FastAPI, Pydantic |
| Config | backend/config.py | Environment variable loading | python-dotenv |
| ORM Models | backend/models.py | Ticket + Insight table definitions | SQLAlchemy |
| Schemas | backend/schemas.py | Request/response validation | Pydantic |
| CSV Ingestion | pipeline/ingest.py | Load CSV, detect Kaggle schema, map columns | pandas |
| Data Cleaning | pipeline/clean.py | Dedup, null fill, timestamp parse, text filter | pandas |
| AI Enrichment | pipeline/enrich.py | Orchestrate LLM/classical per ticket | ai module |
| DB Storage | pipeline/store.py | Upsert tickets, generate insights | SQLAlchemy |
| LLM Client | ai/llm.py | Groq Llama 3.3 70B via OpenAI SDK | openai |
| Embeddings | ai/embeddings.py | OpenAI embeddings + ChromaDB vector store | openai, chromadb |
| Classical ML | ai/classical.py | TF-IDF keywords + TextBlob + templates | textblob |
| Synthetic Data | data/generate_synthetic.py | Faker-based ticket generator (5K-50K) | faker, pandas |
| React Frontend | frontend/src/pages/*.jsx | 5-page dashboard SPA | React, MUI, Recharts |

## 3. Data Flow

```
[CSV File]  or  [Synthetic Generator]
      |                  |
      v                  v
   POST /api/upload   POST /api/generate-sample
      |                  |
      +--------+---------+
               |
               v
      load_csv() -- schema detection and column mapping
               |
               v
      clean()  -- dedup, nulls, timestamp parse, text filter
               |
               v
      enrich_dataframe() -- for each ticket:
         |
         +-- llm.categorize() OR classical.categorize()
         +-- llm.analyze_sentiment() OR classical.analyze_sentiment()
         +-- embeddings.find_similar() -- ChromaDB cosine search
         +-- llm.generate_response(rag_context) OR classical.generate_response()
         +-- embeddings.store_ticket() -- upsert vector
               |
               v
      store_tickets() -- SQLAlchemy upsert to SQLite
               |
               v
      generate_insights() -- top issues + anomaly detection
               |
               v
      [SQLite: tickets + insights tables]
               |
               v
      GET /api/dashboard, /api/tickets, /api/trends, /api/insights
               |
               v
      [React Dashboard -- charts, tables, KPIs]
```

## 4. API Surface

| Method | Endpoint | Request | Response | Notes |
|---|---|---|---|---|
| GET | /api/mode | -- | AI engine status JSON | Shows LLM provider, embedding status, vector count |
| POST | /api/upload | multipart CSV file, sample_size | {status, total_rows, sample_size} | Starts background pipeline |
| POST | /api/generate-sample | count, sample_size | {status, total_rows, sample_size} | Generates synthetic data |
| GET | /api/pipeline/status | -- | PipelineStatus | state: idle, running, done, error |
| POST | /api/reset | -- | {status, message} | Clears SQLite + ChromaDB |
| POST | /api/analyze | {message: string} | AnalyzeResponse | Real-time single-ticket analysis |
| GET | /api/tickets | category, sentiment, min_frustration, search, limit, offset | {total, tickets[]} | Paginated, filterable |
| GET | /api/dashboard | -- | DashboardStats | KPIs, top issues, cost savings |
| GET | /api/trends | -- | {daily_trends[]} | Daily volume + frustration |
| GET | /api/insights | -- | Insight[] | Top issues + anomalies |

## 5. Database Schema

### SQLite: support_platform.db

```
tickets
  id              INTEGER PRIMARY KEY AUTOINCREMENT
  ticket_id       TEXT UNIQUE NOT NULL        -- indexed
  timestamp       DATETIME NOT NULL           -- indexed
  customer_id     TEXT                        -- indexed
  channel         TEXT
  message         TEXT NOT NULL
  agent_reply     TEXT
  product         TEXT
  order_value     REAL
  customer_country TEXT
  resolution_status TEXT
  ai_category     TEXT
  ai_sentiment    TEXT
  ai_frustration  REAL
  ai_response     TEXT
  ai_confidence   REAL
  processed_at    DATETIME

insights
  id              INTEGER PRIMARY KEY AUTOINCREMENT
  insight_type    TEXT                        -- top_issue | anomaly | trend
  category        TEXT
  metric_value    REAL
  description     TEXT
  metadata_json   TEXT                        -- JSON string
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
```

### ChromaDB: chroma_db/ (local persistent)

```
Collection: support_tickets
  - Embedding: 1536 dimensions (text-embedding-3-small)
  - Distance: cosine (HNSW index)
  - Metadata: ai_category, ai_sentiment, agent_reply, resolution_status
  - Document: original ticket message text
```

## 6. Deployment Architecture

```
+-----------------------------------------------------+
|  Docker Container (python:3.11-slim)                 |
|                                                      |
|  +-----------------------------------------------+  |
|  | Uvicorn (port 8000)                            |  |
|  |   FastAPI App                                  |  |
|  |     /api/*  --> backend routes                 |  |
|  |     /       --> static/index.html (React SPA)  |  |
|  |     /assets --> static/assets/ (JS, CSS)       |  |
|  +-----------------------------------------------+  |
|                                                      |
|  Volumes:                                            |
|    ./support_platform.db  (SQLite)                   |
|    ./chroma_db/           (ChromaDB vectors)         |
|                                                      |
|  Health check: curl /api/mode every 30s              |
+-----------------------------------------------------+
         |
    port 8000
         |
+--------v---------+
|  GitHub Actions   |
|  CI Pipeline:     |
|  1. Python import |
|     checks        |
|  2. npm ci + build|
|  3. docker build  |
+------------------+
```

## 7. Scalability Path

```
Current (MVP)                     Production Target
-----------------                 ------------------
SQLite                    -->     PostgreSQL + connection pooling
Background thread         -->     Celery + Redis task queue
Single Uvicorn process    -->     Gunicorn (4-8 workers)
Local ChromaDB            -->     Managed vector DB (Pinecone/Weaviate)
In-memory pipeline state  -->     Redis-backed state
Groq free tier (30 RPM)   -->     Groq paid / self-hosted vLLM
No auth                   -->     OAuth2 / JWT middleware
Single Docker container   -->     Kubernetes (API + worker + DB pods)
CSV upload only           -->     Kafka/SQS stream ingestion
```
