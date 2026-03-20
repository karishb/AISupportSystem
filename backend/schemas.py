"""Pydantic request/response schemas."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class AnalyzeRequest(BaseModel):
    message: str


class AnalyzeResponse(BaseModel):
    category: str
    confidence: float
    sentiment: str
    frustration_score: float
    reasoning: str
    suggested_response: str
    similar_tickets: List[Dict[str, Any]] = []


class TicketOut(BaseModel):
    id: int
    ticket_id: str
    timestamp: str
    customer_id: Optional[str] = None
    channel: Optional[str] = None
    message: str
    agent_reply: Optional[str] = None
    product: Optional[str] = None
    order_value: Optional[float] = None
    ai_category: Optional[str] = None
    ai_sentiment: Optional[str] = None
    ai_frustration: Optional[float] = None
    ai_response: Optional[str] = None
    ai_confidence: Optional[float] = None


class PipelineStatus(BaseModel):
    state: str  # idle, running, done, error
    total: int = 0
    processed: int = 0
    current_step: str = ""
    message: str = ""
    results: Optional[Dict[str, Any]] = None


class DashboardStats(BaseModel):
    total_tickets: int
    avg_frustration: float
    revenue_at_risk: float
    top_issues: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    cost_savings: Dict[str, Any]
    sentiment_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
