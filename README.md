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

## Architecture

Lumen.AI follows a clean 4-layer architecture where each layer communicates only with its immediate neighbor.

```
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT UI  (app.py)                       │
│  ┌──────────┐ ┌───────────┐ ┌────────┐ ┌──────┐ ┌────┐ ┌────┐ │
│  │ Solution │ │ Knowledge │ │  RAG   │ │ Flow │ │SDLC│ │ QA │ │
│  │ Crawler  │ │   Store   │ │  Chat  │ │ Expl │ │Tool│ │Test│ │
│  └────┬─────┘ └─────┬─────┘ └───┬────┘ └──┬───┘ └──┬─┘ └──┬─┘ │
└───────┼─────────────┼───────────┼─────────┼────────┼──────┼────┘
        │             │           │         │        │      │
┌───────┴─────────────┴───────────┴─────────┴────────┴──────┴────┐
│                    BUSINESS LOGIC ENGINE                        │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐  │
│  │  Solution    │ │  Ingestion   │ │   RAG Query Engine     │  │
│  │  Crawler     │ │  Pipeline    │ │  retrieve → rerank →   │  │
│  │  .sln parser │ │  md/pdf/docx │ │  augment → generate    │  │
│  └──────┬───────┘ └──────┬───────┘ └───────────┬────────────┘  │
│         │                │                     │               │
│  ┌──────┴────────────────┴─────────────────────┴────────────┐  │
│  │  SDLC Accelerators                                       │  │
│  │  Bug Assistant | Test Generator | Arch Validator | BRD→TC│  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬───────────────────────────────────┘
                             │
┌────────────────────────────┴───────────────────────────────────┐
│                    STORAGE & INDEXING                           │
│  ┌──────────────────────┐  ┌────────────────────────────────┐  │
│  │  ChromaDB Vector     │  │  SQLite Conversation Memory    │  │
│  │  Store (HNSW cosine) │  │  Multi-turn RAG state          │  │
│  │  ./knowledge_base/   │  │  ./knowledge_base/memory.db    │  │
│  └──────────┬───────────┘  └────────────────────────────────┘  │
└─────────────┼──────────────────────────────────────────────────┘
              │
┌─────────────┴──────────────────────────────────────────────────┐
│                    LLM & EMBEDDINGS                            │
│  ┌────────────────────────┐  ┌───────────────────────────────┐ │
│  │  Ollama LLM Provider   │  │  Ollama Embedding Provider    │ │
│  │  deepseek / llama /    │  │  nomic-embed-text (384-dim)   │ │
│  │  gemma (streaming HTTP)│  │  cosine similarity search     │ │
│  └────────────────────────┘  └───────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### RAG Pipeline Flow

The core intelligence of Lumen.AI is its 5-stage RAG (Retrieval-Augmented Generation) pipeline:

```
User Question
     │
     ▼
┌─────────────────────────────────────────────┐
│ 1. RETRIEVE  (Vector Similarity Search)     │
│    ChromaDB cosine search, top_k=20         │
│    Optional filters: service, domain, type  │
└────────────────────┬────────────────────────┘
                     ▼
┌─────────────────────────────────────────────┐
│ 2. RERANK  (BM25 + Vector Fusion)           │
│    BM25 lexical scoring with IDF            │
│    Fused = α·vector + (1-α)·BM25  (α=0.5)  │
│    Select top_k=5 most relevant chunks      │
└────────────────────┬────────────────────────┘
                     ▼
┌─────────────────────────────────────────────┐
│ 3. AUGMENT  (Context Assembly)              │
│    Reranked chunks + conversation history   │
│    Mode-specific system prompt:             │
│    explain | find | trace | impact | test   │
└────────────────────┬────────────────────────┘
                     ▼
┌─────────────────────────────────────────────┐
│ 4. GENERATE  (LLM Inference)                │
│    Streaming HTTP to Ollama /api/generate   │
│    Live token display with ▌ cursor         │
│    600s read timeout, 900s wall ceiling     │
└────────────────────┬────────────────────────┘
                     ▼
┌─────────────────────────────────────────────┐
│ 5. PARSE & PERSIST                          │
│    Extract sources, confidence, topics      │
│    Detect Mermaid diagrams in response      │
│    Persist to conversation memory (SQLite)  │
└─────────────────────────────────────────────┘
```

### Solution Crawler Flow

The crawler performs deep static analysis of .NET/Angular solutions:

```
.sln file
  │
  ├── Parse project entries (.csproj paths)
  │
  ├── For each project:
  │   ├── Extract TargetFramework (net8.0, etc.)
  │   ├── Extract ProjectReferences (inter-project deps)
  │   ├── Extract NuGet packages + versions
  │   ├── Classify layer (Domain|Application|Infrastructure|API|Tests)
  │   └── Deep analysis (optional):
  │       ├── Configuration nodes (appsettings, env vars)
  │       ├── DI registrations (AddScoped, AddSingleton, etc.)
  │       └── Code symbols (classes, interfaces, attributes)
  │
  ├── Scan C# source files:
  │   ├── Endpoints: [HttpGet/Post/Put/Delete] + [Route] patterns
  │   ├── Consumers: IConsumer<T>, MassTransit state machines
  │   ├── Data models: DbSet<T>, entity properties, relationships
  │   ├── Schedulers: Hangfire, Quartz, IHostedService
  │   └── Integrations: HttpClient, Redis, Consul, S3, gRPC, RabbitMQ
  │
  ├── Angular front-end (auto-detect or explicit path):
  │   ├── Components, selectors, routes
  │   └── API call extraction from services
  │
  ├── Build dependency graph (nodes + edges)
  │
  └── Domain mapping (optional):
      ├── Cluster projects by domain hints
      ├── DDD heuristics: aggregates, events, value objects
      └── Cross-domain contracts (inbound/outbound)
```

### BRD-to-TestCase Flow

```
Upload BRD (PDF/DOCX/MD)
  │
  ├── 1. Text Extraction
  │   ├── PDF → pypdf page-by-page
  │   ├── DOCX → python-docx (paragraphs + tables)
  │   └── MD/TXT → direct read
  │
  ├── 2. Requirement Extraction (LLM)
  │   └── Parse → BRDRequirement[] (id, title, description, priority, category)
  │
  ├── 3. Test Case Generation (LLM)
  │   └── 2-5 cases per requirement:
  │       functional, negative, boundary, security, performance
  │       Each with preconditions, steps[], expected result
  │
  ├── 4. Traceability Matrix
  │   └── req_id → [tc_ids] mapping + coverage %
  │
  └── 5. Output
      ├── Markdown report (download)
      ├── CSV export (download)
      └── Ingest to knowledge store (RAG searchable)
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **UI** | Streamlit + IBM Carbon Design | Web interface with 6 pages |
| **LLM** | Ollama (local) | Text generation, streaming HTTP |
| **Models** | deepseek-coder-v2:16b, llama3.1:8b, gemma4:e4b | Configurable per use case |
| **Embeddings** | nomic-embed-text (384-dim) | Semantic vector search |
| **Vector Store** | ChromaDB (HNSW, cosine) | Document chunk storage + retrieval |
| **Reranking** | BM25 + Vector Fusion | Hybrid lexical + semantic scoring |
| **Memory** | SQLite | Multi-turn conversation persistence |
| **Crawler** | Custom regex parsers | .NET .sln/.csproj/.cs static analysis |
| **PDF Parsing** | pypdf | BRD/FSD text extraction |
| **DOCX Parsing** | python-docx | Word document text + table extraction |
| **PDF Generation** | fpdf2 | Report PDF output |
| **Diagrams** | Mermaid.js (via streamlit-mermaid) | Sequence, flowchart, ER diagrams |
| **Data Models** | Pydantic v2 | Validation + serialization |
| **Config** | YAML | Single source of truth |
| **Architecture Rules** | Custom YAML rulesets | OWASP, NIST, ISO, PCI-DSS compliance |

### Key Dependencies

```
chromadb>=0.4.22          # Vector store with HNSW indexing
tiktoken>=0.5.0           # Token counting for chunking
rank-bm25>=0.2.2          # Lexical reranking
streamlit>=1.28.0         # Web UI framework
streamlit-mermaid>=0.0.4  # Diagram rendering
pypdf>=4.0.0              # PDF text extraction
python-docx>=1.1.0        # Word document parsing
fpdf2>=2.7.0              # PDF report generation
pydantic>=2.0.0           # Data model validation
```

---

## Data Models

### Core Models Hierarchy

```
CrawlReport
├── ProjectInfo[]         — name, path, layer, framework, refs, packages
│   ├── ConfigurationNode[]   — key, value, environment, env_var refs
│   ├── DIRegistration[]      — method, service_type, implementation
│   └── CodeSymbol[]          — name, kind, namespace, DDD markers
├── EndpointInfo[]        — route, method, controller, auth, file:line
├── ConsumerInfo[]        — class, message_type, queue
├── SchedulerInfo[]       — job_name, cron, handler
├── IntegrationPoint[]    — type (http|redis|consul|s3|grpc|rabbitmq)
├── UIComponent[]         — Angular components, selectors, routes, API calls
├── DataModel[]           — entities, properties, relationships (1..* / *..1)
├── BusinessDomain[]      — domain clusters, aggregates, events, contracts
└── DomainContract[]      — cross-domain interface contracts

RAGResponse
├── answer: str           — LLM-generated response
├── sources[]             — SourceReference (file, service, score)
├── confidence: str       — high|medium|low (based on retrieval scores)
├── related_topics[]      — service names, heading paths
├── diagram: str          — Mermaid code (if detected in answer)
└── conversation_id: str  — Multi-turn thread ID

BRDTestReport
├── requirements[]        — BRDRequirement (id, title, priority, category)
├── test_cases[]          — GeneratedTestCase (id, steps, expected, type)
├── traceability: dict    — req_id → [tc_ids] mapping
└── coverage_pct: float   — % of requirements with test cases
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
