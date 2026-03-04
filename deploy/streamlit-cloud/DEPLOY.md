# Deploy to Streamlit Community Cloud

## Quick Steps (Easiest Option!)

1. **Push to GitHub** (if not already):
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/Neo-TDG.git
   git push -u origin main
   ```

2. **Go to** https://share.streamlit.io

3. **Click "New app"** and fill in:
   - **Repository**: `YOUR_USERNAME/Neo-TDG`
   - **Branch**: `main`
   - **Main file path**: `app.py`

4. **Add Secrets** (in Advanced settings > Secrets):
   ```toml
   # .streamlit/secrets.toml format
   OLLAMA_BASE_URL = "https://your-ollama-instance.railway.app"
   ```

5. **Click Deploy!**

## Configuration

The app already has `.streamlit/config.toml` which Streamlit Cloud reads automatically.

## Important Notes

- **Free tier**: 1GB RAM, apps sleep after inactivity
- **Ollama**: Need a remote instance (Streamlit Cloud can't run Ollama locally)
- **ChromaDB**: Works in-memory but resets on reboot. For persistence, use a cloud vector DB
- **No Docker needed** — Streamlit Cloud reads `requirements.txt` directly

## Files Streamlit Cloud Uses
- `app.py` — Entry point
- `requirements.txt` — Dependencies (auto-installed)
- `.streamlit/config.toml` — Theme & server config
- `.streamlit/secrets.toml` — Secrets (set via UI, not committed)
