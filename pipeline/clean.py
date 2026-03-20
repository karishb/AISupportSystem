"""Data cleaning and validation stage of the pipeline."""
import pandas as pd


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate raw ticket data.

    Steps:
    1. Remove duplicate ticket_ids
    2. Fill missing values
    3. Parse timestamps
    4. Filter out very short messages (<10 chars)
    5. Normalize text fields
    """
    original_count = len(df)

    # Deduplicate
    df = df.drop_duplicates(subset=["ticket_id"], keep="first")

    # Fill nulls
    df["message"] = df["message"].fillna("").astype(str)
    df["agent_reply"] = df["agent_reply"].fillna("").astype(str)
    df["product"] = df["product"].fillna("Unknown").astype(str)
    df["channel"] = df["channel"].fillna("email").astype(str)
    df["resolution_status"] = df["resolution_status"].fillna("open").astype(str)

    # Parse timestamps
    if "timestamp" not in df.columns:
        df["timestamp"] = pd.Timestamp.now()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["timestamp"] = df["timestamp"].fillna(pd.Timestamp.now())

    # Replace {product_purchased} placeholder with actual product name
    if "product" in df.columns:
        df["message"] = df.apply(
            lambda r: r["message"].replace("{product_purchased}", str(r["product"])) if "{product_purchased}" in str(r["message"]) else r["message"],
            axis=1
        )

    # Filter short messages
    df = df[df["message"].str.len() >= 10]

    # Ensure required columns exist
    for col in ["ticket_id", "customer_id", "order_value", "customer_country"]:
        if col not in df.columns:
            df[col] = ""

    df = df.reset_index(drop=True)

    cleaned_count = len(df)
    removed = original_count - cleaned_count

    return df, {"original": original_count, "cleaned": cleaned_count, "removed": removed}
