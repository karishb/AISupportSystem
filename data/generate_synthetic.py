"""Generate synthetic customer support ticket dataset (5K-50K rows).

Creates realistic support tickets with temporal patterns including
an anomaly spike in the most recent 2 weeks for demo purposes.
"""
import pandas as pd
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

CATEGORIES = {
    "Billing Inquiry": [
        "I was charged twice for my subscription this month",
        "My invoice shows an incorrect amount of ${amount}",
        "I need to update my payment method on file",
        "Why was I charged after cancelling my subscription?",
        "Can you explain the additional fees on my latest bill?",
    ],
    "Technical Issue": [
        "The app keeps crashing when I try to open my {product}",
        "I'm getting an error code E{code} and can't proceed",
        "The software is extremely slow and freezes constantly",
        "Screen goes black randomly on my {product}",
        "Cannot connect to WiFi after the latest update on my {product}",
    ],
    "Product Inquiry": [
        "Does the {product} come with a warranty?",
        "Is the {product} compatible with Mac?",
        "What are the specifications of the latest {product}?",
        "Can I upgrade my {product} to the pro version?",
        "How does the {product} compare to the previous model?",
    ],
    "Refund Request": [
        "I want a full refund for my {product} order",
        "Product arrived damaged, requesting immediate refund",
        "I returned the {product} 2 weeks ago but haven't received my refund",
        "The product doesn't match the description, need my money back",
        "I was promised a refund of ${amount} but haven't received it",
    ],
    "Account Access": [
        "I can't log into my account, password reset isn't working",
        "My account was locked after too many login attempts",
        "I need to change the email associated with my account",
        "Two-factor authentication is not sending me codes",
        "Someone may have accessed my account without permission",
    ],
    "Shipping Issue": [
        "My order hasn't arrived and it's been {days} days",
        "Package shows delivered but I never received it",
        "Tracking number {tracking} shows no updates for a week",
        "Wrong address on shipping label, need to redirect package",
        "Order was supposed to arrive yesterday, still no update",
    ],
    "Cancellation": [
        "I want to cancel my order #{order_id} immediately",
        "Please cancel my subscription effective today",
        "How do I cancel the auto-renewal on my account?",
        "I changed my mind about the {product}, please cancel",
        "Cancel my order before it ships, order #{order_id}",
    ],
}

PRODUCTS = [
    "Microsoft Surface Pro", "Dell XPS 13", "HP Spectre x360", "MacBook Pro",
    "iPhone", "Samsung Galaxy", "Sony Xperia", "Google Pixel",
    "LG TV", "Nintendo Switch", "Xbox", "PlayStation",
    "Fitbit Versa", "Canon EOS", "GoPro Hero", "Dyson Vacuum",
    "Bose QuietComfort", "Adobe Photoshop", "Microsoft Office",
]

CHANNELS = ["chat", "email", "phone", "social media"]
COUNTRIES = ["US", "UK", "CA", "DE", "FR", "IN", "AU", "BR", "JP"]

AGENT_RESPONSES = {
    "Billing Inquiry": "I've reviewed your billing and corrected the issue. A credit has been applied to your account.",
    "Technical Issue": "I've escalated this to our technical team. Please try restarting the device. We'll follow up within 24 hours.",
    "Product Inquiry": "Thank you for your interest. I've sent you a detailed comparison document via email.",
    "Refund Request": "Your refund has been approved and will be processed within 5-7 business days.",
    "Account Access": "I've reset your account credentials. Please check your email for the reset link.",
    "Shipping Issue": "I've contacted our shipping partner. Your updated tracking information will be sent shortly.",
    "Cancellation": "Your cancellation has been processed. Any applicable refund will be issued within 3-5 days.",
}


def generate_dataset(n: int = 10000) -> pd.DataFrame:
    tickets = []
    recent_date = datetime.now() - timedelta(days=14)

    for i in range(n):
        category = random.choice(list(CATEGORIES.keys()))
        product = random.choice(PRODUCTS)
        template = random.choice(CATEGORIES[category])

        message = template.format(
            product=product, amount=random.randint(20, 500),
            code=random.randint(100, 999), days=random.randint(3, 21),
            tracking=f"TRK{random.randint(100000, 999999)}",
            order_id=f"ORD{random.randint(10000, 99999)}",
        )

        # Add frustration randomly
        if random.random() < 0.25:
            message += " " + random.choice([
                "This is unacceptable!", "Very frustrated with your service!",
                "Terrible experience!", "I'm extremely disappointed.",
                "This is the worst service I've ever had!",
            ])

        timestamp = datetime.now() - timedelta(days=random.randint(0, 90))

        # Inject anomaly: 50% of recent tickets are "Shipping Issue"
        if timestamp > recent_date and random.random() < 0.5:
            category = "Shipping Issue"
            message = random.choice(CATEGORIES[category]).format(
                days=random.randint(7, 21),
                tracking=f"TRK{random.randint(100000, 999999)}",
                order_id=f"ORD{random.randint(10000, 99999)}",
                product=product, amount=0, code=0,
            )

        base_value = random.uniform(50, 800)
        if any(w in message.lower() for w in ["frustrated", "terrible", "worst"]):
            base_value *= random.uniform(1.5, 2.5)

        resolution = random.choices(["closed", "open", "pending"], weights=[0.6, 0.25, 0.15])[0]
        agent_reply = AGENT_RESPONSES[category] if resolution == "closed" else ""

        tickets.append({
            "ticket_id": f"TKT{random.randint(100000, 999999)}",
            "timestamp": timestamp.isoformat(),
            "customer_id": f"CUST{random.randint(1000, 9999)}",
            "channel": random.choice(CHANNELS),
            "message": message,
            "agent_reply": agent_reply,
            "product": product,
            "order_value": round(base_value, 2),
            "customer_country": random.choice(COUNTRIES),
            "resolution_status": resolution,
        })

    df = pd.DataFrame(tickets)
    return df.sort_values("timestamp").reset_index(drop=True)


if __name__ == "__main__":
    df = generate_dataset(10000)
    df.to_csv("data/sample_tickets.csv", index=False)
    print(f"Generated {len(df)} tickets → data/sample_tickets.csv")
