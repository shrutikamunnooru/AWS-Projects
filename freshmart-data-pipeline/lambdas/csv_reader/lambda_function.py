import json
import boto3
import pandas as pd
import io
import logging
from datetime import datetime, timezone

# Set up logging — logs appear in CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Required columns the CSV must have
REQUIRED_COLUMNS = [
    "invoice_id", "branch", "city", "product_line",
    "unit_price", "quantity", "date", "payment", "rating"
]

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    """
    Triggered by S3 ObjectCreated event.
    Reads the uploaded CSV, validates it, and logs metadata.
    """
    # --- Step 1: Extract bucket and file key from the S3 event ---
    # S3 passes this event object automatically when a file is uploaded
    record = event["Records"][0]
    bucket_name = record["s3"]["bucket"]["name"]
    file_key = record["s3"]["object"]["key"]

    logger.info(f"New file detected: s3://{bucket_name}/{file_key}")

    # --- Step 2: Read the CSV from S3 into a pandas DataFrame ---
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        csv_content = response["Body"].read()
        df = pd.read_csv(io.BytesIO(csv_content))
    except Exception as e:
        logger.error(f"Failed to read file from S3: {str(e)}")
        raise

    # --- Step 3: Validate the file ---
    # Check all required columns exist
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Check file is not empty
    if len(df) == 0:
        raise ValueError("File has no data rows.")

    # --- Step 4: Log file metadata ---
    metadata = {
        "file_name": file_key,
        "bucket": bucket_name,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "processed_at": datetime.now(timezone.utc).isoformat()
    }
    logger.info(f"File metadata: {json.dumps(metadata)}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "File validated successfully",
            "metadata": metadata
        })
    }
