# Automate Order Report Generation Using S3 & Lambda

## What it does
Automatically generates a city-wise revenue summary every time a CSV is uploaded to S3.

## Architecture
- `incoming/` folder → triggers Lambda → generates report → saves to `reports/` folder

## Setup Instructions

### 1. S3 Setup
- Create an S3 bucket
- Create two folders: `incoming/` and `reports/`

### 2. Lambda Function
- Runtime: Python 3.11
- Upload `lambda_function.py`
- Set timeout to 30 seconds

### 3. Lambda Layer
- Attach pandas layer using this ARN:
  `arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:13`

### 4. IAM Permissions
- Attach `AmazonS3FullAccess` to the Lambda execution role

### 5. S3 Trigger
- Event type: PUT
- Prefix: `incoming/`
- Suffix: `.csv`

## Sample Output
city,total_revenue
Mumbai,7742.0
Bangalore,6553.0
Delhi,4699.0
Hyderabad,3724.0
Chennai,2793.0
