# Lumen.AI — SDLC Knowledge Engine

AI-powered knowledge engine for software development lifecycle acceleration. Crawl .NET/Angular solutions, build a RAG knowledge store, chat with your codebase, trace flows, generate test cases from BRDs, and validate architecture rules.

## Features

- **Solution Crawler** — Crawl C#/.NET solutions and Angular front-ends, extract endpoints, consumers, schedulers, DI graphs, and data models
- **Knowledge Store** — Ingest crawl reports, PDFs, Markdown, and GitHub repos into a ChromaDB-backed vector store
- **RAG Chat** — Conversational Q&A over your codebase with source citations, confidence scoring, and Mermaid diagrams
- **Flow Explorer** — Trace request flows and explain components with LLM-powered analysis
- **SDLC Tools** — Bug assistant, test generator (unit/integration/edge cases), architecture validator
- **QA Test Generator** — Upload a BRD (PDF/Word) to extract requirements and generate traceable test cases with coverage metrics

## Prerequisites

| Dependency | Purpose | Required |
|---|---|---|
| Python 3.9+ | Runtime | Yes |
| [Ollama](https://ollama.com) | Local LLM + embeddings | Yes (local) |
| Git | Solution crawling, GitHub ingest | Yes |

### Ollama Models

Pull these before first run:

```bash
# LLM (pick one)
ollama pull llama3.1:8b          # fast, good for most tasks
ollama pull deepseek-coder-v2:16b # better code understanding, slower on CPU
ollama pull gemma4:e4b            # balanced

# Embedding model (required)
ollama pull nomic-embed-text
```

---

## Installation

### Option 1: Local (macOS / Linux)

```bash
# 1. Clone
git clone https://github.com/kuntumseroja/Neo-TDG.git
cd Neo-TDG

# 2. Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Ensure Ollama is running
ollama serve &

# 5. Start the app
streamlit run app.py --server.port 8503

# Or use the lifecycle scripts:
./scripts/start.sh        # start
./scripts/stop.sh         # stop
./scripts/lumen.sh status # check status
./scripts/lumen.sh logs   # tail logs
```

The app will be available at **http://localhost:8503**.

### Option 2: VPS / Cloud Server (Ubuntu/Debian)

```bash
# 1. Install system dependencies
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git curl

# 2. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 3. Pull models
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# 4. Clone and setup
git clone https://github.com/kuntumseroja/Neo-TDG.git
cd Neo-TDG
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 5. Run with systemd (production)
# Create a service file:
sudo tee /etc/systemd/system/lumen-ai.service > /dev/null <<'EOF'
[Unit]
Description=Lumen.AI SDLC Knowledge Engine
After=network.target ollama.service

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/Neo-TDG
ExecStart=/path/to/Neo-TDG/.venv/bin/streamlit run app.py \
    --server.port 8503 \
    --server.headless true \
    --server.address 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now lumen-ai

# 6. (Optional) Reverse proxy with nginx
sudo apt install -y nginx
sudo tee /etc/nginx/sites-available/lumen-ai <<'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8503;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/lumen-ai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Access at **http://your-server-ip:8503** (direct) or **http://your-domain.com** (behind nginx).

### Option 3: Hugging Face Spaces

Deploy as a Streamlit Space with cloud LLM providers (no Ollama needed).

```bash
# 1. Fork or clone to your HF account
git clone https://github.com/kuntumseroja/Neo-TDG.git
cd Neo-TDG
git checkout feature-full-cloud

# 2. Add HF remote
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME

# 3. Push to HF (deploys automatically)
git push hf feature-full-cloud:main
```

**Required HF Space settings:**

| Setting | Value |
|---|---|
| SDK | Streamlit |
| Python | 3.10+ |
| Port | 8502 |

**Environment variables** (set in Space Settings > Variables):

| Variable | Example | Purpose |
|---|---|---|
| `GROQ_API_KEY` | `gsk_...` | Groq cloud LLM |
| `TOGETHER_API_KEY` | `tok_...` | Together.ai LLM (alternative) |
| `OPENAI_API_KEY` | `sk-...` | OpenAI LLM (alternative) |

The `.streamlit/config.toml` already includes `enableXsrfProtection = false` and `enableCORS = false` which are required for HF Spaces file uploads to work.

**Live demo:** [https://huggingface.co/spaces/terancammuda/neo-tdg](https://huggingface.co/spaces/terancammuda/neo-tdg)

---

## Configuration

Edit `config.yaml` to customize:

```yaml
llm_providers:
  ollama:
    model: llama3.1:8b        # or deepseek-coder-v2:16b, gemma4:e4b
    base_url: http://localhost:11434
    temperature: 0.3
    max_tokens: 4000

knowledge_store:
  persist_dir: "./knowledge_base"
  embedding:
    model: nomic-embed-text
  chunking:
    strategy: markdown_headers
    max_tokens: 1500
```

### Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_READ_TIMEOUT` | `600` | Per-chunk read timeout (seconds) |
| `OLLAMA_MAX_WALL_SECONDS` | `900` | Max total generation time |
| `LUMEN_PYTHON` | auto-detect | Force a specific Python interpreter |

---

## Project Structure

```
Neo-TDG/
├── app.py                          # Streamlit entry point
├── config.yaml                     # Application configuration
├── requirements.txt                # Python dependencies
├── scripts/
│   ├── lumen.sh                    # Service lifecycle manager
│   ├── start.sh                    # Start wrapper
│   └── stop.sh                     # Stop wrapper
├── src/
│   ├── llm/                        # LLM providers (Ollama, Groq, etc.)
│   ├── knowledge/                  # Vector store, chunker, embeddings
│   ├── rag/                        # RAG engine, reranker, prompts
│   ├── pipeline/                   # Document ingestion pipeline
│   ├── crawler/                    # .NET/Angular solution crawler
│   ├── sdlc/                       # Bug assistant, test gen, arch validator, BRD→TestCase
│   ├── models/                     # Pydantic data models
│   └── ui/                         # Streamlit page components
├── architecture_rules/             # YAML rulesets for architecture validation
├── knowledge_base/                 # ChromaDB persist directory (auto-created)
├── examples/                       # Sample .NET solutions for demo
└── tests/                          # Integration and unit tests
```

---

## Usage

### Quick Start Flow

1. **Start Ollama** — `ollama serve`
2. **Start Lumen.AI** — `streamlit run app.py` or `./scripts/start.sh`
3. **Crawl a solution** — Enter your `.sln` path in Solution Crawler, click "Crawl Solution"
4. **Ingest to knowledge store** — Click "Ingest to Knowledge Store" after crawling
5. **Chat with your code** — Go to RAG Chat, ask questions about your codebase
6. **Generate test cases** — Go to QA Test Generator, upload a BRD PDF/DOCX

### BRD to Test Case

1. Navigate to **QA Test Generator** in the sidebar
2. Upload a BRD document (PDF, DOCX, MD, or TXT)
3. Click **Generate Test Cases**
4. Review results in the tabs: Requirements, Test Cases, Traceability Matrix
5. Download as Markdown or CSV
6. Optionally ingest into the knowledge store for RAG retrieval

---

## License

MIT
