"""FastAPI backend for the Customer Support Insight Platform."""
import io
import threading
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.config import AI_MODE
from backend.models import Ticket, Insight, init_db, get_session
from backend.schemas import AnalyzeRequest, AnalyzeResponse, PipelineStatus
from pipeline.ingest import load_csv
from pipeline.clean import clean
from pipeline.enrich import enrich_ticket, enrich_dataframe
from pipeline.store import store_tickets, generate_insights
from ai import llm, embeddings, classical

app = FastAPI(title="Support Insight API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# --- Pipeline state (in-memory, single worker) ---
_pipeline_state = PipelineStatus(state="idle")
_pipeline_lock = threading.Lock()
_pipeline_cancel = threading.Event()


def _run_pipeline(df: pd.DataFrame, sample_size: Optional[int] = None):
    """Run the full pipeline in a background thread."""
    global _pipeline_state
    _pipeline_cancel.clear()
    try:
        with _pipeline_lock:
            _pipeline_state = PipelineStatus(state="running", current_step="Cleaning data...")

        # 1. Clean
        df_clean, clean_stats = clean(df)
        total = len(df_clean)
        _pipeline_state = PipelineStatus(
            state="running", total=total, processed=0,
            current_step=f"Cleaned: {clean_stats['cleaned']} tickets ({clean_stats['removed']} removed)"
        )

        # 2. Sample if needed
        if sample_size and sample_size < total:
            df_clean = df_clean.sample(n=sample_size, random_state=42).reset_index(drop=True)
            total = len(df_clean)
            _pipeline_state.total = total

        # 3. Enrich with AI
        _pipeline_state.current_step = "Enriching with AI..."

        def on_progress(current, total_count, result):
            if _pipeline_cancel.is_set():
                raise InterruptedError("Pipeline cancelled by user")
            _pipeline_state.processed = current
            _pipeline_state.current_step = (
                f"Processing ticket {current}/{total_count} - "
                f"Category: {result['ai_category']} ({result['ai_confidence']:.0%})"
            )

        df_enriched = enrich_dataframe(df_clean, progress_callback=on_progress)

        # 4. Store
        _pipeline_state.current_step = "Storing to database..."
        stored = store_tickets(df_enriched)

        # 5. Generate insights
        _pipeline_state.current_step = "Generating insights..."
        generate_insights(df_enriched)

        # Done
        cat_dist = df_enriched["ai_category"].value_counts().to_dict() if "ai_category" in df_enriched else {}
        sent_dist = df_enriched["ai_sentiment"].value_counts().to_dict() if "ai_sentiment" in df_enriched else {}

        _pipeline_state = PipelineStatus(
            state="done", total=total, processed=total,
            current_step="Complete",
            message=f"Processed {stored} tickets successfully",
            results={
                "stored": stored,
                "categories": cat_dist,
                "sentiments": sent_dist,
                "avg_frustration": round(df_enriched["ai_frustration"].mean(), 2) if "ai_frustration" in df_enriched else 0,
            }
        )
    except InterruptedError:
        _pipeline_state = PipelineStatus(
            state="done", total=_pipeline_state.total,
            processed=_pipeline_state.processed,
            current_step="Cancelled",
            message=f"Pipeline stopped by user after {_pipeline_state.processed} tickets",
            results={
                "stored": _pipeline_state.processed,
                "categories": {},
                "sentiments": {},
                "avg_frustration": 0,
            }
        )
    except Exception as e:
        _pipeline_state = PipelineStatus(state="error", message=str(e))


# --- Routes ---

@app.get("/api/mode")
def get_mode():
    """Current AI engine configuration."""
    return {
        "mode": "llm" if llm.is_available() else "free",
        "llm_provider": llm.get_provider(),
        "embeddings": "sentence-transformers/all-MiniLM-L6-v2" if embeddings.is_available() else "disabled",
        "vector_db": f"ChromaDB ({embeddings._collection.count()} vectors)" if embeddings._collection else "disabled",
        "categorization": "LLM" if llm.is_available() else "TF-IDF + Keywords",
        "sentiment": "LLM" if llm.is_available() else "TextBlob",
        "responses": "LLM + RAG" if llm.is_available() else "Templates",
    }


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_message(req: AnalyzeRequest):
    """Analyze a single customer message in real-time."""
    result = enrich_ticket(req.message)
    return AnalyzeResponse(
        category=result["ai_category"],
        confidence=result["ai_confidence"],
        sentiment=result["ai_sentiment"],
        frustration_score=result["ai_frustration"],
        reasoning=result.get("ai_reasoning", ""),
        suggested_response=result["ai_response"],
        similar_tickets=result.get("similar_tickets", []),
    )


@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...), sample_size: int = Form(500)):
    """Upload a CSV file and start the processing pipeline."""
    if _pipeline_state.state == "running":
        raise HTTPException(400, "Pipeline already running")
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files accepted")

    contents = await file.read()
    df = load_csv(io.StringIO(contents.decode("utf-8")))

    thread = threading.Thread(target=_run_pipeline, args=(df, sample_size), daemon=True)
    thread.start()

    return {"status": "started", "total_rows": len(df), "sample_size": sample_size}


@app.post("/api/generate-sample")
def generate_sample(count: int = 5000, sample_size: int = 500):
    """Generate synthetic data and run the pipeline."""
    if _pipeline_state.state == "running":
        raise HTTPException(400, "Pipeline already running")

    from data.generate_synthetic import generate_dataset
    df = generate_dataset(count)

    thread = threading.Thread(target=_run_pipeline, args=(df, sample_size), daemon=True)
    thread.start()

    return {"status": "started", "total_rows": count, "sample_size": sample_size}


@app.get("/api/pipeline/status", response_model=PipelineStatus)
def pipeline_status():
    """Get current pipeline processing progress."""
    return _pipeline_state


@app.post("/api/pipeline/stop")
def pipeline_stop():
    """Stop a running pipeline. Already-processed tickets are saved."""
    if _pipeline_state.state != "running":
        raise HTTPException(400, "No pipeline is running")
    _pipeline_cancel.set()
    return {"status": "stopping", "processed_so_far": _pipeline_state.processed}


@app.post("/api/reset")
def reset_data():
    """Clear all tickets and insights for a fresh demo."""
    global _pipeline_state
    session = get_session()
    try:
        session.query(Ticket).delete()
        session.query(Insight).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(500, str(e))
    finally:
        session.close()
    try:
        embeddings.reset()
    except Exception:
        pass
    _pipeline_state = PipelineStatus(state="idle")
    return {"status": "reset", "message": "All data cleared"}


@app.get("/api/tickets")
def get_tickets(
    category: Optional[str] = None,
    sentiment: Optional[str] = None,
    min_frustration: Optional[float] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List tickets with optional filters."""
    session = get_session()
    try:
        query = session.query(Ticket)
        if category:
            query = query.filter(Ticket.ai_category == category)
        if sentiment:
            query = query.filter(Ticket.ai_sentiment == sentiment)
        if min_frustration is not None:
            query = query.filter(Ticket.ai_frustration >= min_frustration)
        if search:
            query = query.filter(Ticket.message.contains(search))

        total = query.count()
        tickets = query.order_by(Ticket.timestamp.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "tickets": [{
                "id": t.id,
                "ticket_id": t.ticket_id,
                "timestamp": t.timestamp.isoformat() if t.timestamp else "",
                "customer_id": t.customer_id,
                "channel": t.channel,
                "message": t.message,
                "agent_reply": t.agent_reply,
                "product": t.product,
                "order_value": t.order_value,
                "resolution_status": t.resolution_status,
                "ai_category": t.ai_category,
                "ai_sentiment": t.ai_sentiment,
                "ai_frustration": t.ai_frustration,
                "ai_response": t.ai_response,
                "ai_confidence": t.ai_confidence,
            } for t in tickets],
        }
    finally:
        session.close()


@app.get("/api/dashboard")
def get_dashboard():
    """Aggregated dashboard statistics."""
    session = get_session()
    try:
        tickets = session.query(Ticket).all()
        if not tickets:
            return {
                "total_tickets": 0, "avg_frustration": 0, "revenue_at_risk": 0,
                "top_issues": [], "anomalies": [], "cost_savings": {},
                "sentiment_distribution": {}, "category_distribution": {},
            }

        df = pd.DataFrame([{
            "ticket_id": t.ticket_id, "timestamp": t.timestamp,
            "ai_category": t.ai_category, "ai_sentiment": t.ai_sentiment,
            "ai_frustration": t.ai_frustration or 0, "order_value": t.order_value or 0,
        } for t in tickets])

        high_frust = df[df["ai_frustration"] > 0.7]

        # Top issues
        top_issues = []
        for cat, group in df.groupby("ai_category"):
            top_issues.append({
                "category": cat,
                "count": len(group),
                "percentage": round(len(group) / len(df) * 100, 1),
                "avg_frustration": round(group["ai_frustration"].mean(), 2),
                "revenue_at_risk": round(group[group["ai_frustration"] > 0.7]["order_value"].sum(), 2),
            })
        top_issues.sort(key=lambda x: x["count"], reverse=True)

        # Anomalies from insights table
        anomalies = []
        for ins in session.query(Insight).filter(Insight.insight_type == "anomaly").all():
            anomalies.append({"category": ins.category, "spike_percentage": ins.metric_value, "description": ins.description})

        # Cost savings projection
        total = len(df)
        automatable = int(total * 0.4)
        hours_saved = round(automatable * 8 / 60, 1)
        cost_saved = round(hours_saved * 25, 2)

        return {
            "total_tickets": total,
            "avg_frustration": round(df["ai_frustration"].mean(), 2),
            "revenue_at_risk": round(high_frust["order_value"].sum(), 2),
            "top_issues": top_issues[:8],
            "anomalies": anomalies,
            "cost_savings": {
                "automatable_tickets": automatable,
                "hours_saved": hours_saved,
                "cost_savings_usd": cost_saved,
            },
            "sentiment_distribution": df["ai_sentiment"].value_counts().to_dict(),
            "category_distribution": df["ai_category"].value_counts().to_dict(),
        }
    finally:
        session.close()


@app.get("/api/trends")
def get_trends():
    """Daily ticket volume and frustration trends."""
    session = get_session()
    try:
        tickets = session.query(Ticket).all()
        if not tickets:
            return {"daily_trends": []}

        df = pd.DataFrame([{
            "timestamp": t.timestamp,
            "ai_frustration": t.ai_frustration or 0,
            "ai_sentiment": t.ai_sentiment,
            "ai_category": t.ai_category,
        } for t in tickets])

        df["date"] = pd.to_datetime(df["timestamp"]).dt.date
        daily = df.groupby("date").agg(
            count=("ai_frustration", "count"),
            avg_frustration=("ai_frustration", "mean"),
        ).reset_index()

        return {
            "daily_trends": [{
                "date": str(row["date"]),
                "count": int(row["count"]),
                "avg_frustration": round(row["avg_frustration"], 2),
            } for _, row in daily.iterrows()],
        }
    finally:
        session.close()


@app.get("/api/insights")
def get_insights():
    """Stored insights (top issues, anomalies)."""
    session = get_session()
    try:
        insights = session.query(Insight).order_by(Insight.created_at.desc()).all()
        return [{
            "id": i.id,
            "type": i.insight_type,
            "category": i.category,
            "value": i.metric_value,
            "description": i.description,
        } for i in insights]
    finally:
        session.close()


# --- Health / Monitoring ---

@app.get("/api/health")
def health_check():
    """Health check with system metrics for monitoring."""
    import time
    start = time.time()
    session = get_session()
    try:
        ticket_count = session.query(Ticket).count()
        insight_count = session.query(Insight).count()
        db_ok = True
    except Exception:
        ticket_count, insight_count, db_ok = 0, 0, False
    finally:
        session.close()

    vector_count = 0
    try:
        if embeddings._collection:
            vector_count = embeddings._collection.count()
    except Exception:
        pass

    return {
        "status": "healthy" if db_ok else "degraded",
        "uptime_check": round(time.time() - start, 4),
        "components": {
            "database": {"status": "up" if db_ok else "down", "tickets": ticket_count, "insights": insight_count},
            "llm": {"status": "up" if llm.is_available() else "down", "provider": llm.get_provider()},
            "vector_db": {"status": "up" if embeddings.is_available() else "down", "vectors": vector_count},
        },
        "pipeline": _pipeline_state.state,
    }


# --- Weekly Report ---

@app.get("/api/report")
def weekly_report():
    """Automated insight report summarizing ticket analysis."""
    session = get_session()
    try:
        tickets = session.query(Ticket).all()
        if not tickets:
            return {"report": "No data available. Upload and process tickets first."}

        df = pd.DataFrame([{
            "ticket_id": t.ticket_id, "timestamp": t.timestamp,
            "ai_category": t.ai_category, "ai_sentiment": t.ai_sentiment,
            "ai_frustration": t.ai_frustration or 0, "order_value": t.order_value or 0,
            "channel": t.channel, "product": t.product,
            "resolution_status": t.resolution_status,
        } for t in tickets])

        total = len(df)
        cat_counts = df["ai_category"].value_counts()
        sent_counts = df["ai_sentiment"].value_counts()
        avg_frust = round(df["ai_frustration"].mean(), 2)
        revenue_at_risk = round(df[df["ai_frustration"] > 0.7]["order_value"].sum(), 2)

        # Top 3 issues
        top_issues = []
        for cat, count in cat_counts.head(3).items():
            cat_df = df[df["ai_category"] == cat]
            top_issues.append({
                "category": cat,
                "count": int(count),
                "percentage": round(count / total * 100, 1),
                "avg_frustration": round(cat_df["ai_frustration"].mean(), 2),
            })

        # Channel breakdown
        channel_dist = df["channel"].value_counts().to_dict()

        # Top products with issues
        product_issues = df.groupby("product").agg(
            count=("ticket_id", "count"),
            avg_frustration=("ai_frustration", "mean"),
        ).sort_values("count", ascending=False).head(5)

        top_products = [{
            "product": idx, "tickets": int(row["count"]),
            "avg_frustration": round(row["avg_frustration"], 2),
        } for idx, row in product_issues.iterrows()]

        # Resolution rate
        resolved = len(df[df["resolution_status"] == "closed"])
        resolution_rate = round(resolved / total * 100, 1) if total > 0 else 0

        # Recommendations
        recommendations = []
        worst_cat = cat_counts.index[0] if len(cat_counts) > 0 else None
        if worst_cat:
            recommendations.append(f"Focus on reducing '{worst_cat}' tickets ({cat_counts.iloc[0]} tickets, {round(cat_counts.iloc[0]/total*100)}% of volume)")
        if avg_frust > 0.6:
            recommendations.append(f"Average frustration is high ({avg_frust}/1.0). Review response SLAs and agent training.")
        if revenue_at_risk > 1000:
            recommendations.append(f"${revenue_at_risk:,.0f} revenue at risk from high-frustration tickets. Prioritize these customers.")
        neg_pct = round(sent_counts.get("negative", 0) / total * 100, 1)
        if neg_pct > 50:
            recommendations.append(f"{neg_pct}% of tickets have negative sentiment. Investigate root causes.")

        return {
            "period": "Current dataset",
            "summary": {
                "total_tickets": total,
                "avg_frustration": avg_frust,
                "revenue_at_risk": revenue_at_risk,
                "resolution_rate": resolution_rate,
            },
            "sentiment_distribution": sent_counts.to_dict(),
            "top_issues": top_issues,
            "channel_breakdown": channel_dist,
            "top_products_by_issues": top_products,
            "recommendations": recommendations,
        }
    finally:
        session.close()


# --- Multilingual ---

@app.post("/api/detect-language")
def detect_language(req: AnalyzeRequest):
    """Detect the language of a customer message."""
    text = req.message[:500]
    detected = _detect_lang(text)
    return detected


def _detect_lang(text: str) -> dict:
    """Simple language detection using common word frequency."""
    text_lower = text.lower()
    lang_markers = {
        "en": ["the", "is", "and", "to", "in", "for", "of", "with", "my", "have", "not", "please"],
        "es": ["el", "la", "de", "en", "que", "por", "los", "del", "las", "una", "con"],
        "fr": ["le", "la", "de", "en", "les", "des", "est", "que", "une", "dans", "pour"],
        "de": ["der", "die", "und", "den", "das", "ist", "ein", "eine", "nicht", "von"],
        "pt": ["de", "que", "em", "um", "uma", "para", "com", "por", "como", "mais"],
        "it": ["il", "di", "che", "la", "per", "un", "una", "del", "della", "sono"],
        "ja": ["の", "は", "に", "を", "で", "が", "と", "た", "し", "です"],
        "zh": ["的", "是", "在", "了", "不", "我", "有", "这", "他", "们"],
        "hi": ["है", "के", "में", "का", "की", "को", "से", "और", "एक", "पर"],
    }
    words = text_lower.split()
    scores = {}
    for lang, markers in lang_markers.items():
        score = sum(1 for w in words if w in markers)
        scores[lang] = score
    best_lang = max(scores, key=scores.get) if scores else "en"
    confidence = scores[best_lang] / max(len(words), 1)
    if confidence < 0.05:
        best_lang = "en"
        confidence = 0.5
    lang_names = {"en": "English", "es": "Spanish", "fr": "French", "de": "German",
                  "pt": "Portuguese", "it": "Italian", "ja": "Japanese", "zh": "Chinese", "hi": "Hindi"}
    return {
        "language_code": best_lang,
        "language": lang_names.get(best_lang, best_lang),
        "confidence": round(min(confidence * 2, 1.0), 2),
    }


@app.post("/api/translate-and-analyze")
def translate_and_analyze(req: AnalyzeRequest):
    """Detect language, translate if needed, then analyze."""
    lang_info = _detect_lang(req.message)

    if lang_info["language_code"] != "en" and llm.is_available():
        # Ask LLM to translate then analyze in one call
        try:
            from ai.llm import _get_client, _model, CATEGORIES
            client, key_idx = _get_client()
            if client:
                resp = client.chat.completions.create(
                    model=_model,
                    messages=[
                        {"role": "system", "content": (
                            "The user message is in " + lang_info["language"] + ". "
                            "First translate it to English, then analyze it. Return valid JSON:\n"
                            "{\n"
                            '  "translated_message": "English translation",\n'
                            '  "category": "one of: ' + ", ".join(CATEGORIES) + '",\n'
                            '  "confidence": 0.0-1.0,\n'
                            '  "sentiment": "positive|neutral|negative",\n'
                            '  "frustration_score": 0.0-1.0,\n'
                            '  "suggested_response": "2-3 sentence response in ' + lang_info["language"] + '"\n'
                            "}\nRespond with valid JSON only."
                        )},
                        {"role": "user", "content": req.message[:1000]}
                    ],
                    temperature=0,
                    max_tokens=400,
                )
                import json
                text = resp.choices[0].message.content.strip()
                if text.startswith("```"):
                    text = text.split("```")[1].removeprefix("json").strip()
                result = json.loads(text)
                return {
                    "original_language": lang_info,
                    "translated_message": result.get("translated_message", req.message),
                    "category": result.get("category", "General Inquiry"),
                    "confidence": result.get("confidence", 0.8),
                    "sentiment": result.get("sentiment", "neutral"),
                    "frustration_score": result.get("frustration_score", 0.5),
                    "suggested_response": result.get("suggested_response", ""),
                }
        except Exception as e:
            print(f"Translate error: {e}")

    # English or fallback — use normal analysis
    result = enrich_ticket(req.message)
    return {
        "original_language": lang_info,
        "translated_message": req.message,
        "category": result["ai_category"],
        "confidence": result["ai_confidence"],
        "sentiment": result["ai_sentiment"],
        "frustration_score": result["ai_frustration"],
        "suggested_response": result["ai_response"],
    }


# --- Serve React SPA in production ---
@app.get("/")
def root():
    index = Path(__file__).resolve().parent.parent / "static" / "index.html"
    if index.is_file():
        return FileResponse(str(index))
    return {"message": "Support Insight API v2.0", "docs": "/docs"}


_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        file_path = _static_dir / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_static_dir / "index.html"))
