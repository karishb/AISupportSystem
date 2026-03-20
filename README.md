# AI-Powered Customer Support Insight Platform

A full-stack platform that ingests customer support tickets, enriches them with AI-driven categorization, sentiment analysis, and frustration detection, then surfaces actionable business insights through an interactive dashboard. Uses Groq Llama 3.3 70B for LLM inference, OpenAI embeddings with ChromaDB for RAG-based response generation, and scikit-learn TF-IDF + TextBlob as a zero-cost fallback.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- (Optional) Groq API key -- free at [console.groq.com](https://console.groq.com)
- (Optional) OpenAI API key -- for embeddings and vector search

### Install

```bash
# Clone
git clone https://github.com/<your-org>/AISupportSystem.git
cd AISupportSystem

# Backend
pip install -r requirements.txt

# Frontend
cd frontend && npm ci && cd ..
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
AI_MODE=llm
DATABASE_URL=sqlite:///support_platform.db
```

If no keys are provided, the system runs in **free mode** using TF-IDF keyword matching and TextBlob sentiment analysis -- no API calls required.

### Run

```bash
# Terminal 1 -- Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 -- Frontend
cd frontend && npm run dev
```

Open [http://localhost:5173](http://localhost:5173) for the dashboard or [http://localhost:8000/docs](http://localhost:8000/docs) for the API explorer.

---

## Project Structure

```
AISupportSystem/
  backend/
    config.py          # Environment variables, model names, limits
    models.py          # SQLAlchemy ORM (Ticket, Insight tables)
    schemas.py         # Pydantic request/response models
    main.py            # FastAPI routes and pipeline orchestration
  ai/
    llm.py             # Groq Llama 3.3 70B (categorize, sentiment, response)
    embeddings.py      # OpenAI text-embedding-3-small + ChromaDB vector store
    classical.py       # TF-IDF keyword scoring + TextBlob fallback
  pipeline/
    ingest.py          # CSV loading and Kaggle schema mapping
    clean.py           # Deduplication, null handling, text normalization
    enrich.py          # AI enrichment orchestrator (LLM or classical)
    store.py           # SQLite persistence and insight generation
  frontend/
    src/pages/
      Upload.jsx       # CSV upload and synthetic data generation
      Dashboard.jsx    # KPI cards, charts, cost-savings projection
      Tickets.jsx      # Filterable ticket table with AI annotations
      Assistant.jsx    # Real-time single-message analysis
      Analytics.jsx    # Trend charts and anomaly detection
  data/
    generate_synthetic.py  # Faker-based synthetic ticket generator (5K-50K rows)
  docs/
    ARCHITECTURE.md    # Component diagram and data flow
    DESIGN_DOC.md      # Design decisions and tradeoffs
    BUSINESS_INSIGHTS.md # Business value and metrics framework
  Dockerfile           # Multi-stage build (Node + Python)
  docker-compose.yml   # Single-service deployment
  .github/workflows/ci.yml  # CI: lint, import checks, Docker build
```

---

## Features

| Feature | LLM Mode | Free Mode |
|---|---|---|
| Ticket categorization | Groq Llama 3.3 70B zero-shot | TF-IDF keyword scoring |
| Sentiment analysis | LLM structured JSON output | TextBlob polarity |
| Frustration detection | LLM reasoning + score | Keyword frequency + polarity |
| Response generation | LLM + RAG (similar tickets) | Template-based |
| Semantic search | OpenAI embeddings + ChromaDB | Disabled |
| CSV upload | Yes | Yes |
| Synthetic data generator | Yes (Faker, 5K-50K rows) | Yes |
| Real-time analysis | Yes | Yes |
| Dashboard with charts | Recharts visualizations | Recharts visualizations |
| Anomaly detection | Mean + 2-sigma on daily counts | Mean + 2-sigma on daily counts |
| Cost-savings projection | 40% automation estimate | 40% automation estimate |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/mode` | Current AI engine configuration |
| POST | `/api/upload` | Upload CSV and start pipeline |
| POST | `/api/generate-sample` | Generate synthetic data and process |
| GET | `/api/pipeline/status` | Pipeline progress (state, step, count) |
| POST | `/api/reset` | Clear all tickets, insights, and vectors |
| POST | `/api/analyze` | Analyze a single message in real time |
| GET | `/api/tickets` | List tickets with filters (category, sentiment, frustration, search) |
| GET | `/api/dashboard` | Aggregated KPIs, top issues, cost savings |
| GET | `/api/trends` | Daily ticket volume and frustration trends |
| GET | `/api/insights` | Stored insights (top issues, anomalies) |

---

## Docker Deployment

```bash
# Build and run
docker compose up --build

# Or build manually
docker build -t support-insight-platform .
docker run -p 8000:8000 --env-file .env support-insight-platform
```

The Dockerfile uses a multi-stage build: Node 20 Alpine compiles the React frontend, then Python 3.11-slim serves both the API and the static SPA. A health check pings `/api/mode` every 30 seconds.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React 18, Material UI, Recharts | Dashboard SPA |
| Backend | FastAPI, SQLAlchemy, Pydantic | REST API and ORM |
| LLM | Groq Llama 3.3 70B Versatile | Categorization, sentiment, response generation |
| Embeddings | OpenAI text-embedding-3-small | Semantic similarity for RAG |
| Vector DB | ChromaDB (persistent, cosine) | Similar ticket retrieval |
| Classical ML | scikit-learn TF-IDF, TextBlob | Zero-cost fallback pipeline |
| Database | SQLite | Ticket and insight storage |
| Containerization | Docker, Docker Compose | Single-command deployment |
| CI/CD | GitHub Actions | Import checks, frontend build, Docker build |

---

## License

MIT
