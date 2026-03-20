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

    # Replace all {placeholder} patterns in messages
    import re
    if "product" in df.columns:
        def _replace_placeholders(row):
            msg = str(row["message"])
            product = str(row["product"])
            # Replace {product_purchased} and variants with actual product name
            msg = re.sub(r'\{[Pp]roduct[_\w]*\}', product, msg)
            # Replace other common placeholders with sensible defaults
            msg = re.sub(r'\{error_message\}', 'an unexpected error', msg)
            msg = re.sub(r'\{order_\w+\}', 'ORD-' + str(row.get("ticket_id", "000"))[:6], msg)
            msg = re.sub(r'\{(?:name|Name|user)\}', 'Customer', msg)
            msg = re.sub(r'\{(?:device_name|model|model_name)\}', product, msg)
            # Remove any remaining {placeholder} patterns
            msg = re.sub(r'\{[^}]+\}', '', msg)
            return msg
        df["message"] = df.apply(_replace_placeholders, axis=1)

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
