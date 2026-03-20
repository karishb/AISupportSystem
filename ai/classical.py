"""Classical ML fallback: TF-IDF categorization + TextBlob sentiment.

Used when no LLM API key is available. Provides basic but functional
categorization and sentiment analysis without any API costs.
"""
from typing import Dict
from textblob import TextBlob

CATEGORY_KEYWORDS = {
    "Billing Inquiry": ["bill", "charge", "invoice", "payment", "price", "cost", "fee", "subscription"],
    "Technical Issue": ["error", "bug", "crash", "not working", "broken", "slow", "freeze", "glitch"],
    "Product Inquiry": ["feature", "how to", "does it", "compatible", "specs", "information", "details"],
    "Refund Request": ["refund", "money back", "return", "reimburse", "credit", "chargeback"],
    "Account Access": ["login", "password", "locked", "access", "can't log", "reset", "account"],
    "Shipping Issue": ["shipping", "delivery", "tracking", "late", "lost", "package", "arrived"],
    "Cancellation": ["cancel", "cancellation", "stop", "terminate", "end subscription", "unsubscribe"],
    "General Inquiry": ["help", "question", "info", "support"],
}

FRUSTRATION_WORDS = [
    "terrible", "awful", "horrible", "worst", "unacceptable", "ridiculous",
    "frustrated", "angry", "disappointed", "furious", "disgusting", "pathetic",
    "!!!", "???", "never again", "waste of time",
]


def categorize(message: str) -> Dict:
    """Categorize using keyword frequency scoring."""
    msg = message.lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in msg)
        if score > 0:
            scores[category] = score
    if not scores:
        return {"category": "General Inquiry", "confidence": 0.3}
    best = max(scores, key=scores.get)
    conf = min(1.0, scores[best] / 3.0)
    return {"category": best, "confidence": round(conf, 2)}


def analyze_sentiment(message: str) -> Dict:
    """Analyze sentiment using TextBlob polarity + frustration keywords."""
    blob = TextBlob(message)
    polarity = blob.sentiment.polarity

    if polarity > 0.1:
        sentiment = "positive"
    elif polarity < -0.1:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    msg_lower = message.lower()
    frust_count = sum(1 for w in FRUSTRATION_WORDS if w in msg_lower)
    frustration = max(0.0, min(1.0, -polarity + frust_count * 0.15))

    if frustration > 0.7:
        reasoning = "High frustration: strong negative language and emotional indicators"
    elif frustration > 0.4:
        reasoning = "Moderate frustration with some negative sentiment"
    else:
        reasoning = "Low frustration, relatively calm tone"

    return {"sentiment": sentiment, "frustration_score": round(frustration, 2), "reasoning": reasoning}


RESPONSE_TEMPLATES = {
    "Billing Inquiry": "I understand your concern about billing. Let me review your account and resolve this promptly. You should see any corrections within 3-5 business days.",
    "Technical Issue": "I'm sorry you're experiencing technical difficulties. I've escalated this to our engineering team with high priority. We'll follow up within 24 hours with a fix.",
    "Product Inquiry": "Thank you for your interest. I'd be happy to provide detailed information about our product. Let me address your specific questions.",
    "Refund Request": "I understand your request for a refund. I've initiated the process and you should see the credit in your account within 5-7 business days.",
    "Account Access": "I'm sorry for the access issues. I've reset your credentials. Please check your email for a password reset link.",
    "Shipping Issue": "I apologize for the shipping delay. I've contacted our logistics team and will provide you with an updated tracking number shortly.",
    "Cancellation": "I've processed your cancellation request. Any applicable refund will be issued within 3-5 business days.",
    "General Inquiry": "Thank you for contacting us. I'm here to help with any questions. Let me look into this right away.",
}


def generate_response(message: str, category: str) -> str:
    """Generate response from templates."""
    return RESPONSE_TEMPLATES.get(category, RESPONSE_TEMPLATES["General Inquiry"])
