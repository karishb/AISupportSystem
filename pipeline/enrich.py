"""AI enrichment stage: categorize, analyze sentiment, generate responses.

Optimizations:
- Combined categorize+sentiment in 1 LLM call (saves 33% API quota)
- Rate limiting built into ai/llm.py (stays under Groq 30 req/min)
- Falls back to classical ML if LLM call fails
- Skips tickets already in database (no duplicate processing)
"""
import pandas as pd
from typing import Dict, Callable, Optional
from datetime import datetime

from ai import llm, embeddings, classical
from backend.models import Ticket, get_session, init_db


def get_processed_ticket_ids() -> set:
    """Get ticket IDs already in the database to skip re-processing."""
    init_db()
    session = get_session()
    try:
        ids = {t.ticket_id for t in session.query(Ticket.ticket_id).all()}
        return ids
    finally:
        session.close()


def enrich_ticket(message: str, category_hint: str = "") -> Dict:
    """Enrich a single ticket with AI analysis.

    Uses 2 LLM calls max per ticket:
    1. categorize + sentiment (combined)
    2. generate response (with RAG context)
    Falls back to classical ML if LLM fails.
    """
    # 1. Combined categorize + sentiment (1 API call instead of 2)
    llm_result = None
    if llm.is_available():
        llm_result = llm.categorize_and_analyze(message)

    if llm_result:
        category = llm_result["category"]
        confidence = llm_result["confidence"]
        sentiment = llm_result["sentiment"]
        frustration = llm_result["frustration_score"]
        reasoning = llm_result["reasoning"]
    else:
        # Fallback to classical ML
        cat_result = classical.categorize(message)
        sent_result = classical.analyze_sentiment(message)
        category = cat_result["category"]
        confidence = cat_result["confidence"]
        sentiment = sent_result["sentiment"]
        frustration = sent_result["frustration_score"]
        reasoning = sent_result["reasoning"]

    # 2. Find similar tickets for RAG context
    similar_context = ""
    similar_tickets = []
    if embeddings.is_available():
        similar_tickets = embeddings.find_similar(message, top_k=3, category=category)
        if similar_tickets:
            similar_context = "\n".join(
                f"- Customer: {s['message'][:100]}... Resolution: {s['resolution'][:100]}"
                for s in similar_tickets if s.get("resolution")
            )

    # 3. Generate response (1 API call)
    response = None
    if llm.is_available():
        response = llm.generate_response(message, category, similar_context)
    if not response:
        response = classical.generate_response(message, category)

    return {
        "ai_category": category,
        "ai_confidence": confidence,
        "ai_sentiment": sentiment,
        "ai_frustration": frustration,
        "ai_reasoning": reasoning,
        "ai_response": response,
        "similar_tickets": similar_tickets,
    }


def enrich_dataframe(
    df: pd.DataFrame,
    progress_callback: Optional[Callable] = None,
) -> pd.DataFrame:
    """Enrich all tickets in a DataFrame with AI analysis.

    Skips tickets already in the database. Rate-limited automatically.
    """
    # Check which tickets are already processed
    existing_ids = get_processed_ticket_ids()
    skipped = 0

    results = []
    total = len(df)

    for idx, row in df.iterrows():
        ticket_id = str(row.get("ticket_id", f"TKT{idx}"))
        msg = str(row.get("message", ""))

        # Skip already processed
        if ticket_id in existing_ids:
            skipped += 1
            results.append(_empty_result())
            if progress_callback:
                progress_callback(len(results), total, {"ai_category": "skipped", "ai_confidence": 0})
            continue

        if len(msg) < 10:
            results.append(_empty_result())
            if progress_callback:
                progress_callback(len(results), total, {"ai_category": "too short", "ai_confidence": 0})
            continue

        result = enrich_ticket(msg)

        # Store embedding in ChromaDB for future RAG lookups
        if embeddings.is_available():
            meta = {
                "ai_category": result["ai_category"],
                "ai_sentiment": result["ai_sentiment"],
                "agent_reply": str(row.get("agent_reply", ""))[:500],
                "resolution_status": str(row.get("resolution_status", "")),
            }
            embeddings.store_ticket(ticket_id, msg, meta)

        results.append(result)

        if progress_callback:
            progress_callback(len(results), total, result)

    if skipped > 0:
        print(f"Skipped {skipped} already-processed tickets")

    # Merge AI columns into DataFrame
    ai_df = pd.DataFrame([{
        "ai_category": r["ai_category"],
        "ai_confidence": r["ai_confidence"],
        "ai_sentiment": r["ai_sentiment"],
        "ai_frustration": r["ai_frustration"],
        "ai_response": r["ai_response"],
    } for r in results])

    df = pd.concat([df.reset_index(drop=True), ai_df], axis=1)
    df["processed_at"] = datetime.utcnow()

    return df


def _empty_result() -> Dict:
    return {
        "ai_category": "General Inquiry",
        "ai_confidence": 0.0,
        "ai_sentiment": "neutral",
        "ai_frustration": 0.5,
        "ai_reasoning": "Skipped",
        "ai_response": "",
        "similar_tickets": [],
    }
