import csv
import io
import os
from datetime import datetime, timezone
import functions_framework
from google.cloud import bigquery, storage

storage_client = storage.Client()
bq_client = bigquery.Client()
QUARANTINE_BUCKET = os.environ.get("QUARANTINE_BUCKET", "")


def _quarantine_blob(bucket, blob, file_name, reason):
    print(f"Quarantining {file_name}: {reason}")
    if QUARANTINE_BUCKET:
        q_bucket = storage_client.bucket(QUARANTINE_BUCKET)
        bucket.copy_blob(blob, q_bucket, new_name=f"bad/{file_name}")
        blob.delete()


@functions_framework.cloud_event
def process_csv(cloud_event):
    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]

    if file_name.startswith("bad/") or not file_name.lower().endswith(".csv"):
        print(f"Skipping file: {file_name}")
        return

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    content = blob.download_as_text(encoding="utf-8")

    reader = csv.DictReader(io.StringIO(content))
    rows_to_insert = []
    processed_at = datetime.now(timezone.utc).isoformat()

    try:
        for row in reader:
            tx_id = (row.get("transaction_id") or "").strip()
            raw_amount = (row.get("amount") or "").strip()
            if not tx_id or not raw_amount:
                raise ValueError(f"Missing transaction_id or amount in {file_name}")
            rows_to_insert.append({
                "transaction_id": tx_id,
                "amount": float(raw_amount),
                "processed_at": processed_at,
                "source_file": file_name,
            })
    except ValueError as exc:
        _quarantine_blob(bucket, blob, file_name, str(exc))
        return

    if not rows_to_insert:
        _quarantine_blob(bucket, blob, file_name, "CSV contained no valid data rows")
        return

    table_ref = bq_client.dataset("sales_data").table("daily_transactions")
    errors = bq_client.insert_rows_json(table_ref, rows_to_insert)
    if errors:
        raise RuntimeError(f"BigQuery insert errors: {errors}")

    print(f"Inserted {len(rows_to_insert)} rows from {file_name}")
