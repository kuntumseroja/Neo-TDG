# Deploy to Railway

## Quick Steps

1. **Sign up** at https://railway.app

2. **Install Railway CLI** (optional):
   ```bash
   npm install -g @railway/cli
   railway login
   ```

3. **Deploy from GitHub**:
   - Click **"New Project"** > **"Deploy from GitHub Repo"**
   - Select your Neo-TDG repository
   - Railway auto-detects the Dockerfile

4. **Set Environment Variables** (in Railway dashboard > Variables):
   ```
   PORT=7860
   OLLAMA_BASE_URL=https://your-ollama-instance.railway.app
   ```

5. **Add Ollama as a Service** (optional — run Ollama on Railway too):
   - Click **"+ New"** > **"Docker Image"**
   - Image: `ollama/ollama`
   - This gives you `OLLAMA_BASE_URL=http://ollama.railway.internal:11434`

## Railway-Specific Config

Railway uses the `Dockerfile` at project root. It also respects:
- `PORT` env var (auto-set by Railway)
- The health check endpoint at `/_stcore/health`

## Pricing
- **Trial**: $5 free credit
- **Hobby**: $5/month + usage (more than enough for this app)
- **Pro**: $20/month for teams

## Why Railway for Neo-TDG?
- Can run **both Streamlit + Ollama** as separate services in one project
- Internal networking between services (no public Ollama exposure)
- Persistent volumes for knowledge_base data
- Auto-deploy on git push
