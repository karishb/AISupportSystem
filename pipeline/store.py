"""Database storage and insight generation stage."""
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List

from backend.models import Ticket, Insight, init_db, get_session


def store_tickets(df: pd.DataFrame) -> int:
    """Store processed tickets to database. Returns count stored."""
    init_db()
    session = get_session()
    stored = 0

    try:
        for _, row in df.iterrows():
            # Skip tickets that weren't actually processed
            if row.get("ai_category") == "skipped" or row.get("ai_category") == "too short":
                continue
            tid = str(row.get("ticket_id", ""))
            existing = session.query(Ticket).filter_by(ticket_id=tid).first()
            if existing:
                # Update existing ticket with new AI results
                existing.ai_category = row.get("ai_category")
                existing.ai_sentiment = row.get("ai_sentiment")
                existing.ai_frustration = row.get("ai_frustration")
                existing.ai_response = row.get("ai_response")
                existing.ai_confidence = row.get("ai_confidence")
                existing.processed_at = row.get("processed_at", datetime.utcnow())
            else:
                ticket = Ticket(
                    ticket_id=tid,
                    timestamp=row.get("timestamp", datetime.utcnow()),
                    customer_id=str(row.get("customer_id", "")),
                    channel=str(row.get("channel", "")),
                    message=str(row.get("message", "")),
                    agent_reply=str(row.get("agent_reply", "")),
                    product=str(row.get("product", "")),
                    order_value=float(row.get("order_value", 0)),
                    customer_country=str(row.get("customer_country", "")),
                    resolution_status=str(row.get("resolution_status", "")),
                    ai_category=row.get("ai_category"),
                    ai_sentiment=row.get("ai_sentiment"),
                    ai_frustration=row.get("ai_frustration"),
                    ai_response=row.get("ai_response"),
                    ai_confidence=row.get("ai_confidence"),
                    processed_at=row.get("processed_at", datetime.utcnow()),
                )
                session.add(ticket)
            stored += 1

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

    return stored


def generate_insights(df: pd.DataFrame):
    """Calculate and store business insights from processed tickets."""
    init_db()
    session = get_session()

    try:
        # Clear old insights
        session.query(Insight).delete()

        # Top issues by category
        if "ai_category" in df.columns:
            cat_counts = df["ai_category"].value_counts()
            for cat, count in cat_counts.items():
                cat_df = df[df["ai_category"] == cat]
                avg_frust = cat_df["ai_frustration"].mean() if "ai_frustration" in cat_df else 0
                revenue = cat_df["order_value"].sum() if "order_value" in cat_df else 0
                session.add(Insight(
                    insight_type="top_issue",
                    category=cat,
                    metric_value=float(count),
                    description=f"{cat}: {count} tickets ({count/len(df)*100:.1f}%), avg frustration {avg_frust:.2f}",
                    metadata_json=json.dumps({
                        "count": int(count),
                        "percentage": round(count / len(df) * 100, 1),
                        "avg_frustration": round(float(avg_frust), 2),
                        "revenue_at_risk": round(float(revenue), 2),
                    }),
                ))

        # Anomaly detection (mean + 2 sigma on daily counts per category)
        if "timestamp" in df.columns and "ai_category" in df.columns:
            df_copy = df.copy()
            df_copy["date"] = pd.to_datetime(df_copy["timestamp"]).dt.date
            daily = df_copy.groupby(["date", "ai_category"]).size().reset_index(name="count")

            for cat in df_copy["ai_category"].unique():
                cat_data = daily[daily["ai_category"] == cat]
                if len(cat_data) < 7:
                    continue
                mean = cat_data["count"].mean()
                std = cat_data["count"].std()
                if std == 0:
                    continue
                threshold = mean + 2 * std
                recent = cat_data.tail(7)
                if recent["count"].max() > threshold:
                    spike = round(((recent["count"].sum() / (mean * 7)) - 1) * 100, 1)
                    session.add(Insight(
                        insight_type="anomaly",
                        category=cat,
                        metric_value=spike,
                        description=f"Spike in {cat}: {spike}% above baseline",
                        metadata_json=json.dumps({
                            "recent_count": int(recent["count"].sum()),
                            "baseline": int(mean * 7),
                            "spike_percentage": spike,
                        }),
                    ))

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Insight generation error: {e}")
    finally:
        session.close()
