# Deploy to Hugging Face Spaces

## Quick Steps

1. **Create a new Space** at https://huggingface.co/new-space
   - Select **Docker** as the SDK
   - Choose a name (e.g., `neo-tdg`)

2. **Copy the README.md metadata** from this folder to your project root:
   ```bash
   cp deploy/huggingface/README.md ./README.md
   ```

3. **Push to Hugging Face**:
   ```bash
   # Add HF remote
   git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/neo-tdg

   # Push
   git push hf main
   ```

4. **Configure Secrets** (in Space Settings > Variables):
   - `OLLAMA_BASE_URL` — Your Ollama API endpoint (e.g., a remote Ollama instance)

## Important Notes

- **Ollama**: HF Spaces doesn't run Ollama locally. You need either:
  - A remote Ollama instance (e.g., on Railway or a VPS)
  - Switch to HuggingFace Inference API (modify `config.yaml`)
  - Use a free API like Groq or Together AI

- **Persistent Storage**: Knowledge base resets on redeploy. Use HF Datasets for persistence.

- **Free tier**: 2 vCPU, 16GB RAM — sufficient for the Streamlit app + ChromaDB.
