import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client("lambda")

# Name of the worker Lambda to invoke
WORKER_LAMBDA_NAME = "data_transformer_worker"


def lambda_handler(event, context):
    """
    Controller Lambda — triggered by S3 event.
    Extracts the S3 file path and invokes the worker Lambda to do the transforms.
    Think of this as the "manager" that delegates work.
    """
    # --- Step 1: Extract S3 file info from the event ---
    record = event["Records"][0]
    bucket_name = record["s3"]["bucket"]["name"]
    file_key = record["s3"]["object"]["key"]

    logger.info(f"Orchestrator triggered for: s3://{bucket_name}/{file_key}")

    # --- Step 2: Build the payload to send to the worker ---
    worker_payload = {
        "source_bucket": bucket_name,
        "file_key": file_key
    }

    # --- Step 3: Invoke the worker Lambda synchronously ---
    # InvocationType='RequestResponse' means we WAIT for the worker to finish
    # (vs 'Event' which is fire-and-forget)
    try:
        response = lambda_client.invoke(
            FunctionName=WORKER_LAMBDA_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps(worker_payload)
        )

        # Read and parse the worker's response
        response_payload = json.loads(response["Payload"].read())

        # Check if the worker itself returned an error
        if response.get("FunctionError"):
            raise Exception(f"Worker Lambda failed: {response_payload}")

        worker_result = json.loads(response_payload.get("body", "{}"))
        logger.info(f"Worker completed successfully: {worker_result}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "rows_processed": worker_result.get("rows_processed"),
                "rows_filtered": worker_result.get("rows_filtered"),
                "output_file_path": worker_result.get("output_file_path")
            })
        }

    except Exception as e:
        logger.error(f"Orchestrator error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "failed",
                "error": str(e)
            })
        }
