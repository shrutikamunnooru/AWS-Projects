#!/bin/bash
# deploy.sh — Deploys a Lambda function zip to AWS
# Usage: ./scripts/deploy.sh <function_name> <zip_file_path>
#
# Called by CodeBuild's post_build phase for each Lambda function.

set -e  # Exit immediately if any command fails

FUNCTION_NAME=$1
ZIP_FILE=$2
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Validate arguments
if [ -z "$FUNCTION_NAME" ] || [ -z "$ZIP_FILE" ]; then
    echo "ERROR: Usage: deploy.sh <function_name> <zip_file_path>"
    exit 1
fi

if [ ! -f "$ZIP_FILE" ]; then
    echo "ERROR: Zip file not found: $ZIP_FILE"
    exit 1
fi

echo "[$TIMESTAMP] Deploying $FUNCTION_NAME from $ZIP_FILE..."

# Update the Lambda function code in AWS
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region us-east-1

DEPLOY_STATUS=$?

if [ $DEPLOY_STATUS -eq 0 ]; then
    echo "[$TIMESTAMP] SUCCESS: $FUNCTION_NAME deployed successfully"
else
    echo "[$TIMESTAMP] FAILED: Deployment of $FUNCTION_NAME failed with exit code $DEPLOY_STATUS"
    exit 1
fi
