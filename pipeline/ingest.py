"""CSV loading and schema mapping for the data pipeline."""
import pandas as pd
import hashlib
import random
from typing import Optional

# Expected columns from the Kaggle dataset
KAGGLE_COLUMN_MAP = {
    "Ticket ID": "ticket_id",
    "Customer Name": "customer_id",
    "Ticket Channel": "channel",
    "Ticket Description": "message",
    "Resolution": "agent_reply",
    "Product Purchased": "product",
    "Date of Purchase": "timestamp",
    "Ticket Status": "resolution_status",
    "Ticket Type": "original_type",
    "Ticket Subject": "subject",
    "Customer Age": "customer_age",
    "Customer Gender": "customer_gender",
    "Ticket Priority": "priority",
    "Customer Satisfaction Rating": "satisfaction_rating",
    "First Response Time": "first_response_time",
    "Time to Resolution": "time_to_resolution",
}

PRODUCTS_ORDER_VALUES = {
    "Microsoft Surface Pro": 999, "Dell XPS 13": 1199, "HP Spectre x360": 1249,
    "MacBook Pro": 2499, "iPhone": 1099, "Samsung Galaxy": 899,
    "Sony Xperia": 799, "Google Pixel": 699, "LG TV": 1499,
    "Nintendo Switch": 299, "Xbox": 499, "PlayStation": 499,
    "Fitbit Versa": 229, "Autodesk Fusion": 495, "Adobe Photoshop": 263,
    "Microsoft Office": 149, "Canon EOS": 1799, "GoPro Hero": 399,
    "Dyson Vacuum": 599, "Bose QuietComfort": 349,
}

COUNTRIES = ["US", "US", "US", "UK", "UK", "CA", "DE", "FR", "IN", "AU", "BR", "JP"]


def load_csv(file_path_or_buffer, sample_size: Optional[int] = None) -> pd.DataFrame:
    """Load CSV and map columns to our standard schema."""
    df = pd.read_csv(file_path_or_buffer)

    # Detect if this is the Kaggle dataset by checking column names
    if "Ticket ID" in df.columns and "Ticket Description" in df.columns:
        df = _map_kaggle_schema(df)
    elif "ticket_id" in df.columns and "message" in df.columns:
        pass  # Already in our schema
    else:
        # Try to find message-like and id-like columns
        msg_cols = [c for c in df.columns if any(kw in c.lower() for kw in ["description", "message", "text", "body"])]
        id_cols = [c for c in df.columns if any(kw in c.lower() for kw in ["id", "ticket"])]
        if msg_cols:
            df = df.rename(columns={msg_cols[0]: "message"})
        if id_cols:
            df = df.rename(columns={id_cols[0]: "ticket_id"})
        if "message" not in df.columns:
            raise ValueError(f"Cannot find message column. Available: {list(df.columns)}")
        if "ticket_id" not in df.columns:
            df["ticket_id"] = [f"TKT{i:06d}" for i in range(len(df))]

    # Sample if requested
    if sample_size and sample_size < len(df):
        df = df.sample(n=sample_size, random_state=42)

    return df


def _map_kaggle_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Map Kaggle Customer Support Ticket Dataset to our schema."""
    df = df.rename(columns={k: v for k, v in KAGGLE_COLUMN_MAP.items() if k in df.columns})

    # Hash customer names for privacy
    if "customer_id" in df.columns:
        df["customer_id"] = df["customer_id"].apply(
            lambda x: "CUST" + hashlib.md5(str(x).encode()).hexdigest()[:6].upper()
        )

    # Parse timestamp
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["timestamp"] = df["timestamp"].fillna(pd.Timestamp.now())

    # Generate order_value based on product
    random.seed(42)
    if "product" in df.columns:
        df["order_value"] = df["product"].apply(
            lambda p: round(PRODUCTS_ORDER_VALUES.get(str(p), 200) * random.uniform(0.8, 1.2), 2)
        )
    else:
        df["order_value"] = [round(random.uniform(50, 500), 2) for _ in range(len(df))]

    # Generate customer_country
    df["customer_country"] = [random.choice(COUNTRIES) for _ in range(len(df))]

    # Map resolution_status
    if "resolution_status" in df.columns:
        status_map = {"Open": "open", "Closed": "closed", "Pending Customer Response": "pending"}
        df["resolution_status"] = df["resolution_status"].map(status_map).fillna("open")

    return df
