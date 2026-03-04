# Deploy to Google Cloud Run

## Prerequisites
- Google Cloud account with billing enabled
- `gcloud` CLI installed: https://cloud.google.com/sdk/docs/install

## Quick Steps

```bash
# 1. Set your project
gcloud config set project YOUR_PROJECT_ID

# 2. Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com

# 3. Build and push to Artifact Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/neo-tdg

# 4. Deploy to Cloud Run
gcloud run deploy neo-tdg \
  --image gcr.io/YOUR_PROJECT_ID/neo-tdg \
  --platform managed \
  --region asia-southeast1 \
  --port 7860 \
  --memory 2Gi \
  --cpu 2 \
  --allow-unauthenticated \
  --set-env-vars="OLLAMA_BASE_URL=https://your-ollama-host"
```

## Pricing
- **Free tier**: 2 million requests/month, 360k vCPU-seconds
- For a demo app, this is essentially free

## Notes
- Cloud Run scales to zero when idle (no cost when not in use)
- Cold start takes ~10-15 seconds for Streamlit
- Knowledge base is ephemeral (use Cloud Storage for persistence)
- Best for production workloads that need auto-scaling
