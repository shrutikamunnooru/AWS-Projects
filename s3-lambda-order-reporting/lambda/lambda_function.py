import boto3
import pandas as pd
from io import StringIO
from datetime import datetime

s3 = boto3.client("s3")

def lambda_handler(event, context):
    print("Lambda triggered by S3 upload")

    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    input_key = event["Records"][0]["s3"]["object"]["key"]

    print(f"Bucket: {bucket_name}")
    print(f"Input file: {input_key}")

    response = s3.get_object(Bucket=bucket_name, Key=input_key)
    csv_content = response["Body"].read().decode("utf-8")

    df = pd.read_csv(StringIO(csv_content))

    df["revenue"] = df["quantity"] * df["price"]

    summary_df = (
        df.groupby("city", as_index=False)["revenue"]
        .sum()
        .rename(columns={"revenue": "total_revenue"})
        .sort_values(by="total_revenue", ascending=False)
    )

    output_buffer = StringIO()
    summary_df.to_csv(output_buffer, index=False)

    today = datetime.today().strftime("%Y-%m-%d")
    output_key = f"reports/city_revenue_summary_{today}.csv"

    s3.put_object(
        Bucket=bucket_name,
        Key=output_key,
        Body=output_buffer.getvalue()
    )

    print(f"Report saved to: {output_key}")

    return {
        "statusCode": 200,
        "message": "City revenue summary generated successfully",
        "output_file": output_key
    }