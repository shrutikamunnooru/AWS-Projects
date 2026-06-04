# FreshMart Data Pipeline

Serverless, event-driven data pipeline built on AWS Lambda, S3, and CodeBuild.

## Architecture

```
CSV uploaded to S3 (freshmart-raw-data)
         ↓  [S3 ObjectCreated event]
  csv_reader_lambda
  - Validates columns and row count
  - Logs file metadata to CloudWatch
         ↓  [triggers]
  pipeline_orchestrator
  - Controller Lambda
  - Invokes worker Lambda with S3 file path
         ↓  [Lambda invoke]
  data_transformer_worker
  - Adds total_amount, rating_category columns
  - Filters zero-value rows
  - Parses dates
  - Writes cleaned CSV to freshmart-processed-data
```

## AWS Prerequisites

- Two S3 buckets: `freshmart-raw-data` (source) and `freshmart-processed-data` (destination)
- Three Lambda functions created in AWS console: `csv_reader_lambda`, `pipeline_orchestrator`, `data_transformer_worker`
- IAM role for Lambda with permissions: `s3:GetObject`, `s3:PutObject`, `lambda:InvokeFunction`, `logs:CreateLogGroup`, `logs:PutLogEvents`
- AWS CodeBuild project (`freshmart-pipeline-build`) connected to this GitHub repo, triggering on `main` branch
- CodeBuild IAM role with permissions: `lambda:UpdateFunctionCode`, `s3:*`, `logs:*`

## S3 Event Trigger Setup

1. Go to `freshmart-raw-data` bucket → Properties → Event notifications
2. Create notification: Event type = `s3:ObjectCreated:*`, suffix = `.csv`
3. Destination = Lambda function `csv_reader_lambda`

## First-Time Manual Deployment

```bash
# csv_reader
cd lambdas/csv_reader
pip install -r requirements.txt -t package/
cp lambda_function.py package/
cd package && zip -r ../../../../artifacts/csv_reader.zip . && cd ../../../..

# orchestrator
zip -j artifacts/orchestrator.zip lambdas/orchestrator/lambda_function.py

# transformer
cd lambdas/transformer
pip install -r requirements.txt -t package/
cp lambda_function.py package/
cd package && zip -r ../../../../artifacts/transformer.zip . && cd ../../../..

# Deploy
./scripts/deploy.sh csv_reader_lambda     artifacts/csv_reader.zip
./scripts/deploy.sh pipeline_orchestrator artifacts/orchestrator.zip
./scripts/deploy.sh data_transformer_worker artifacts/transformer.zip
```

## CI/CD Deployments (Subsequent)

Push to `main` branch → CodeBuild auto-triggers → runs `buildspec.yml` → deploys all three Lambdas automatically.

Feature branches do NOT trigger CodeBuild.

## Branching Strategy

- `main` — production only, merged via PR from `develop`
- `develop` — integration branch
- `feature/*` — individual feature branches (e.g. `feature/csv-reader`)

## Design Decisions

- `csv_reader_lambda` handles validation only — keeps responsibilities clean
- Orchestrator uses `InvocationType='RequestResponse'` (synchronous) so it can return a summary of what the worker did
- pandas pinned to `2.2.2` for Lambda compatibility
- `deploy.sh` uses `set -e` so any failure stops the deployment immediately
