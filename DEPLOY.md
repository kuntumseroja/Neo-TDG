# Neo-TDG Cloud Deployment Guide

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Cloud Platform                        │
│  (HF Spaces / Railway / Render / Cloud Run)             │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Streamlit   │  │  ChromaDB    │  │  Sentence     │  │
│  │  Frontend    │──│  (embedded)  │──│  Transformers │  │
│  │  Port 7860   │  │  Vector DB   │  │  Embeddings   │  │
│  └──────┬───────┘  └──────────────┘  └──────────────┘  │
│         │                                               │
└─────────┼───────────────────────────────────────────────┘
          │ API call
          ▼
   ┌──────────────┐
   │  Cloud LLM   │
   │  (Groq FREE) │
   │  or OpenAI   │
   │  or Together  │
   └──────────────┘
```

## Quickest: Deploy with Groq (FREE LLM)

### Step 1: Get a free Groq API key
1. Go to https://console.groq.com/keys
2. Sign up (free) and create an API key
3. Save it — you'll need it in Step 3

### Step 2: Set up cloud config
```bash
cp config.cloud.yaml config.yaml
```

### Step 3: Choose your platform

---

### Option A: Hugging Face Spaces (Free, easiest)

```bash
# 1. Copy HF metadata to root
cp deploy/huggingface/README.md ./README.md

# 2. Create a Space at https://huggingface.co/new-space (SDK: Docker)

# 3. Add secret: GROQ_API_KEY = your-key

# 4. Push
git remote add hf https://huggingface.co/spaces/YOUR_USER/neo-tdg
git push hf main
```

---

### Option B: Streamlit Community Cloud (Free, zero Docker)

```bash
# 1. Push to GitHub
git push origin main

# 2. Go to https://share.streamlit.io
# 3. Connect your repo, set main file: app.py
# 4. Add secret: GROQ_API_KEY = your-key
# 5. Deploy!
```

---

### Option C: Railway ($5 free credit)

```bash
# 1. Install CLI
npm install -g @railway/cli && railway login

# 2. Create and deploy
railway init
railway up

# 3. Set env vars in dashboard:
#    GROQ_API_KEY = your-key
#    PORT = 7860
```

---

### Option D: Docker Compose (any VPS/local)

```bash
# Cloud LLM mode (no GPU needed):
export GROQ_API_KEY="your-key"
cp config.cloud.yaml config.yaml
docker compose up app

# Self-hosted Ollama mode (needs GPU):
docker compose --profile full up
```

---

### Option E: Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/neo-tdg
gcloud run deploy neo-tdg \
  --image gcr.io/PROJECT_ID/neo-tdg \
  --port 7860 --memory 2Gi --cpu 2 \
  --allow-unauthenticated \
  --set-env-vars="GROQ_API_KEY=your-key"
```

---

## LLM Provider Comparison

| Provider | Free Tier | Speed | Models | Best For |
|----------|-----------|-------|--------|----------|
| **Groq** | 30 req/min, 14.4K/day | Ultra-fast (LPU) | Llama 3.3 70B, Gemma, Mixtral | Demo & dev |
| **Together** | $1 free credit | Fast | Llama 3.3, Qwen, DeepSeek | Open-source models |
| **OpenAI** | Pay-per-use | Fast | GPT-4o, GPT-4o-mini | Production quality |
| **Ollama** | Free (self-host) | Depends on hardware | Any GGUF model | Full control |

## Switching LLM Provider

Edit `config.yaml`:
```yaml
# Change this line:
default_llm_provider: groq    # or: openai, together, ollama
```

And set the corresponding API key:
```bash
export GROQ_API_KEY="..."      # for groq
export OPENAI_API_KEY="..."    # for openai
export TOGETHER_API_KEY="..."  # for together
export OLLAMA_BASE_URL="..."   # for remote ollama
```

## File Structure

```
Neo-TDG/
├── Dockerfile              # Universal container (all platforms)
├── docker-compose.yml      # Full stack (app + optional Ollama)
├── Procfile                # Heroku/Railway (non-Docker)
├── render.yaml             # Render auto-deploy
├── runtime.txt             # Python version
├── config.cloud.yaml       # Cloud config template
├── requirements.txt        # Dependencies (includes cloud SDKs)
├── src/llm/                # Standalone LLM providers
│   ├── base.py             # BaseLLM interface
│   ├── ollama_llm.py       # Ollama provider
│   ├── groq_llm.py         # Groq provider (free!)
│   ├── openai_llm.py       # OpenAI + Together provider
│   └── factory.py          # LLMFactory (creates any provider)
└── deploy/
    ├── huggingface/        # HF Spaces config
    ├── streamlit-cloud/    # Streamlit Cloud guide
    ├── railway/            # Railway config
    └── gcloud/             # Google Cloud Run guide
```
