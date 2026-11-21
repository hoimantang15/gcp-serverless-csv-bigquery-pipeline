# gcp-serverless-csv-bigquery-pipeline

# Automated CSV-to-BigQuery Serverless Pipeline (GCP ACE Portfolio)

An event-driven, serverless data pipeline on Google Cloud Platform built for a **Google Cloud Associate Cloud Engineer (ACE)** portfolio, with automated CI/CD via **GitHub Actions** and **Workload Identity Federation** (zero static service account keys).

## Architecture

1. **Ingest:** CSV files are uploaded to Cloud Storage bucket `ace-csv-pipeline-project01-raw-csv`.
2. **Trigger:** An Eventarc trigger (`google.cloud.storage.object.v1.finalized`) invokes the 2nd gen Cloud Run function `process-csv-file` (Python 3.12) in `us-central1`.
3. **Process & Route:**
   - Valid records are loaded into BigQuery table `sales_data.daily_transactions`.
   - Invalid files/records are routed to `ace-csv-pipeline-project01-quarantine-csv`.
4. **Observe:** Function execution and errors are monitored in Cloud Logging.

## Security & CI/CD (Workload Identity Federation)

- **Keyless Auth:** GitHub Actions exchanges an OIDC token via `github-pool` / `github-provider` (`assertion.repository` scoped to `hoimantang15/gcp-serverless-csv-bigquery-pipeline`).
- **IAM Least Privilege:** Uses custom service account `csv-pipeline-sa` with `roles/iam.workloadIdentityUser` and `roles/iam.serviceAccountTokenCreator` bound to the repository principal set, plus scoped runtime/deployment permissions.
- **Workflow:** `.github/workflows/deploy.yml` deploys `process-csv-file` (`--gen2`) on pushes to `main` and manual `workflow_dispatch`.

### GitHub Actions Repository Variables
- `WIF_PROVIDER`
- `GCP_SA_EMAIL`
- `RAW_BUCKET`
- `QUARANTINE_BUCKET`

## Verification

Upload a sample CSV to the raw bucket:

```bash
gcloud storage cp test_valid.csv gs://ace-csv-pipeline-project01-raw-csv/
