# FreshMart Data Pipeline

A serverless, event-driven data pipeline built on AWS Lambda, S3, and CodeBuild CI/CD.

## Project Overview

FreshMart Analytics is a grocery retail company that uploads daily store sales CSV files to S3 every morning. This pipeline automatically processes those files the moment they land — transforming raw sales data and writing cleaned output to a destination bucket — with zero manual intervention.

All infrastructure is deployed and updated automatically through a CI/CD pipeline connected to GitHub.

---

## Architecture

```
CSV uploaded to S3 (freshmart-raw-data)
         ↓  [S3 ObjectCreated event]
  pipeline_orchestrator
  - Controller Lambda — triggered directly by S3
  - Invokes the worker Lambda with the S3 file path
         ↓  [Lambda invoke — synchronous]
  data_transformer_worker
  - Adds total_amount column (unit_price * quantity)
  - Adds rating_category (Low / Medium / High)
  - Filters rows where quantity = 0 or unit_price = 0
  - Converts date column to datetime format
  - Writes cleaned CSV to freshmart-processed-data-usmunno
         ↓
  CloudWatch Logs
  - All Lambda execution logs visible under /aws/lambda/*
```

> **Note:** `csv_reader_lambda` is a standalone validation function that can be triggered separately for file metadata logging. The main pipeline is triggered through `pipeline_orchestrator`.

---

## AWS Services Used

| Service | Resource | Purpose |
|---|---|---|
| Amazon S3 | freshmart-raw-data | Source bucket — receives raw CSV uploads |
| Amazon S3 | freshmart-processed-data-usmunno | Destination bucket — stores cleaned output |
| AWS Lambda | pipeline_orchestrator | Controller — triggered by S3, invokes worker |
| AWS Lambda | data_transformer_worker | Performs all data transformations |
| AWS Lambda | csv_reader_lambda | Validates CSV columns and logs file metadata |
| AWS CodeBuild | freshmart-pipeline-build | CI/CD — auto-deploys Lambdas on push to main |
| Amazon CloudWatch | /aws/lambda/* | Execution logs for all Lambda functions |
| AWS IAM | Lambda execution role | Permissions for S3, Lambda invoke, CloudWatch |

---

## Dataset

The pipeline processes daily sales CSV files with the following schema:

| Column | Type | Example |
|---|---|---|
| invoice_id | string | INV-00101 |
| branch | string | A, B, or C |
| city | string | Kanpur, Lucknow, Agra |
| product_line | string | Electronics, Grocery, Fashion, Health |
| unit_price | float | 45.99 |
| quantity | integer | 3 |
| date | string (YYYY-MM-DD) | 2025-11-15 |
| payment | string | Cash, Credit Card, UPI |
| rating | float | 7.5 |

---

## Repository Structure

```
freshmart-data-pipeline/
├── lambdas/
│   ├── csv_reader/
│   │   ├── lambda_function.py
│   │   └── requirements.txt
│   ├── orchestrator/
│   │   └── lambda_function.py
│   └── transformer/
│       ├── lambda_function.py
│       └── requirements.txt
├── scripts/
│   └── deploy.sh
├── buildspec.yml
├── sales.csv               ← sample input data
└── README.md
```

---

## AWS Prerequisites

Before deploying, set up the following in AWS:

**S3 Buckets**
- `freshmart-raw-data` — source bucket (Block all public access: ON)
- `freshmart-processed-data-usmunno` — destination bucket (Block all public access: ON)

**Lambda Functions**
Create three Lambda functions in AWS Console (Python 3.11, x86_64):
- `csv_reader_lambda`
- `pipeline_orchestrator`
- `data_transformer_worker`

**IAM Role for Lambda**
Attach to all three Lambda functions:
- `AmazonS3FullAccess`
- `AWSLambda_FullAccess`

**S3 Event Trigger**
- Go to `freshmart-raw-data` → Properties → Event notifications
- Event type: `s3:ObjectCreated:*`, suffix: `.csv`
- Destination: Lambda function → `pipeline_orchestrator`

**CodeBuild Project**
- Project name: `freshmart-pipeline-build`
- Source: GitHub repo connected via OAuth
- Webhook filter: `HEAD_REF = ^refs/heads/main$` (only triggers on main branch)
- Buildspec: inline editor (see buildspec.yml in this repo)
- CodeBuild IAM role must have: `AWSLambda_FullAccess`, `AmazonS3FullAccess`

---

## CI/CD Pipeline

The project uses AWS CodeBuild for automated deployments:

```
Push code to main branch on GitHub
         ↓  [webhook triggers CodeBuild]
CodeBuild pulls latest code from GitHub
         ↓
Installs pandas (Linux-compatible binaries)
         ↓
Packages each Lambda as a zip with dependencies
         ↓
Runs deploy.sh → aws lambda update-function-code
         ↓
All 3 Lambda functions updated in AWS automatically
```

**Feature branches do NOT trigger CodeBuild** — only merges to `main` trigger a deployment.

---

## Branching Strategy

| Branch | Purpose |
|---|---|
| `main` | Production-ready code — merged via PR from develop |
| `develop` | Integration branch for ongoing work |
| `feature/csv-reader` | CSV reader Lambda implementation |
| `feature/orchestrator` | Orchestrator Lambda implementation |
| `feature/cicd-setup` | CI/CD buildspec and deploy script |

Pull request flow: `feature/*` → `develop` → `main`

---

## Testing the Pipeline

1. Upload `sales.csv` (or any CSV with the required columns) to `freshmart-raw-data`
2. S3 event fires automatically within seconds
3. Check **CloudWatch → Log groups → /aws/lambda/pipeline_orchestrator** for execution logs
4. Check **S3 → freshmart-processed-data-usmunno → processed/** for the cleaned output CSV

---

## Key Design Decisions

- **Orchestrator pattern:** `pipeline_orchestrator` uses `InvocationType='RequestResponse'` (synchronous invoke) so it can capture the worker's result and return a summary with rows processed, rows filtered, and output file path
- **Linux-compatible pandas:** pip install uses `--platform manylinux2014_x86_64 --only-binary=:all:` to download pre-compiled Linux binaries — required because Lambda runs on Amazon Linux, not the developer's local OS
- **Separation of concerns:** `csv_reader_lambda` handles validation only; `data_transformer_worker` handles transformation only — each function has a single responsibility
- **deploy.sh uses `set -e`:** Any deployment failure stops the script immediately rather than silently continuing

---

## Challenges & Debugging

| Error | Root Cause | Fix |
|---|---|---|
| `GLIBC_2.27 not found` | pandas bundled from Mac was incompatible with Lambda's Amazon Linux runtime | Added `--platform manylinux2014_x86_64 --only-binary=:all:` to pip install |
| `YAML_FILE_ERROR: Expected Commands[0] to be of string type` | Inline comments in buildspec.yml commands list broke CodeBuild's YAML parser | Removed all inline comments from commands |
| `Could not find pandas==2.2.2 for manylinux platform` | That specific version had no Linux binary on PyPI | Removed version pin, used latest available |
| `AccessDeniedException: lambda:UpdateFunctionCode` | CodeBuild service role missing Lambda permissions | Attached `AWSLambda_FullAccess` to CodeBuild IAM role |
| `repository not found for primary source` | GitHub URL in CodeBuild was missing the repo name | Updated to full URL including repo name |
| `cp: directory package does not exist` | pip install doesn't create target directory automatically | Added `mkdir -p` before pip install commands |
