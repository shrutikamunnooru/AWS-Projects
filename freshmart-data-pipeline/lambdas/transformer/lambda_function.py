import json
import boto3
import pandas as pd
import io
import logging
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")

# Destination bucket where cleaned files go
DESTINATION_BUCKET = "freshmart-processed-data-usmunno"


def lambda_handler(event, context):
    """
    Worker Lambda — invoked by the orchestrator.
    Performs all data transformations and writes output to destination S3 bucket.
    """
    source_bucket = event["source_bucket"]
    file_key = event["file_key"]

    logger.info(f"Worker transforming: s3://{source_bucket}/{file_key}")

    # --- Step 1: Read the CSV from S3 ---
    try:
        response = s3_client.get_object(Bucket=source_bucket, Key=file_key)
        csv_content = response["Body"].read()
        df = pd.read_csv(io.BytesIO(csv_content))
    except Exception as e:
        logger.error(f"Failed to read file: {str(e)}")
        raise

    original_row_count = len(df)
    logger.info(f"Loaded {original_row_count} rows")

    # --- Step 2: Filter out bad rows ---
    # Remove rows where quantity or unit_price is 0 (meaningless sales records)
    df = df[(df["quantity"] != 0) & (df["unit_price"] != 0)]
    rows_filtered = original_row_count - len(df)
    logger.info(f"Filtered out {rows_filtered} rows with zero quantity or price")

    # --- Step 3: Add total_amount column ---
    # Simple derived metric: how much did this line item cost in total
    df["total_amount"] = df["unit_price"] * df["quantity"]

    # --- Step 4: Add rating_category column ---
    # Buckets raw rating float into a human-readable category
    def categorize_rating(rating):
        if rating < 5:
            return "Low"
        elif rating <= 7:
            return "Medium"
        else:
            return "High"

    df["rating_category"] = df["rating"].apply(categorize_rating)

    # --- Step 5: Convert date column to proper datetime format ---
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    # Drop rows where date couldn't be parsed (NaT values)
    df = df.dropna(subset=["date"])
    # Store back as ISO string for CSV compatibility
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    rows_processed = len(df)

    # --- Step 6: Write cleaned CSV to destination S3 bucket ---
    # Build output file key: processed/sales_2025-11-15.csv
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    original_filename = file_key.split("/")[-1].replace(".csv", "")
    output_key = f"processed/{original_filename}_cleaned_{timestamp}.csv"

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)

    try:
        s3_client.put_object(
            Bucket=DESTINATION_BUCKET,
            Key=output_key,
            Body=csv_buffer.getvalue(),
            ContentType="text/csv"
        )
        logger.info(f"Wrote cleaned file to s3://{DESTINATION_BUCKET}/{output_key}")
    except Exception as e:
        logger.error(f"Failed to write output file: {str(e)}")
        raise

    return {
        "statusCode": 200,
        "body": json.dumps({
            "rows_processed": rows_processed,
            "rows_filtered": rows_filtered,
            "output_file_path": f"s3://{DESTINATION_BUCKET}/{output_key}"
        })
    }
