# PRD: TechDocGen RAG Expansion — AI-Powered SDLC Knowledge Engine

> **Executable PRD for Cursor / Claude Code**
> Version: 1.0 | Date: 2026-03-03
> Product: TechDocGen-AI RAG Edition
> Client: DJP (Direktorat Jenderal Pajak) — CoreTax System
> Base Repository: `TechDocGen/`

---

## 1. Executive Summary

TechDocGen currently generates technical documentation from source code using LLM enrichment. This PRD expands TechDocGen into a **RAG-powered SDLC Knowledge Engine** that stores all generated documentation as retrievable knowledge, enabling developers, architects, and testers to query the CoreTax codebase in natural language, accelerate bug resolution, and improve software delivery quality.

The expanded system adds: a vector knowledge store, IDE integration (VS Code & Visual Studio), solution/project crawling intelligence, and conversational SDLC assistance — all operating within DJP's air-gapped infrastructure.

---

## 2. Problem Statement

DJP's CoreTax system spans 50+ microservices with CQRS/DDD patterns, MassTransit messaging, Angular micro-frontends, and complex cross-service validations. Current challenges:

- **Knowledge fragmentation**: Documentation exists in PDFs, wikis, and developers' heads. New team members take months to become productive.
- **Slow bug resolution**: Tracing a bug across services requires understanding message flows, domain events, and shared dependencies — information scattered across repos.
- **No single source of truth**: Architecture decisions, component relationships, and integration contracts are not queryable.
- **IDE disconnect**: Developers context-switch between code editor and documentation constantly.

---

## 3. Vision

Transform TechDocGen from a documentation generator into a **living knowledge base** that:

1. **Ingests** — Crawls .sln solutions, discovers all projects, dependencies, schedulers, integrations, and UI components automatically
2. **Understands** — Parses and indexes code into a semantic knowledge graph with vector embeddings
3. **Stores** — Persists generated documentation + code understanding in a RAG-ready vector store
4. **Assists** — Answers natural-language questions about architecture, flow, logic, and components directly inside VS Code / Visual Studio
5. **Accelerates** — Helps developers write code faster, testers design test cases, and architects validate designs against the actual codebase

---

## 4. Target Users & Personas

| Persona | Use Case | Example Query |
|---------|----------|---------------|
| **Developer** | Understand unfamiliar service, fix bugs faster | "How does the TaxPayment command flow from API to database?" |
| **Architect** | Validate design, find dependencies | "Which services depend on TaxpayerRegistration bounded context?" |
| **Tester/QA** | Design test cases, understand edge cases | "What validations exist in the InvoiceSubmission handler?" |
| **Tech Lead** | Onboard team members, review impact | "What would break if we change the TaxPayer aggregate?" |
| **DevOps** | Understand schedulers and infrastructure | "List all Hangfire recurring jobs and their schedules" |

---

## 5. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    IDE LAYER (VS Code / Visual Studio)       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Chat Panel   │  │ Inline Hints │  │ Context Menu      │  │
│  │ (RAG Query)  │  │ (Hover Docs) │  │ "Explain Flow"    │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────────┘  │
└─────────┼──────────────────┼─────────────────┼──────────────┘
          │                  │                 │
          ▼                  ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    API GATEWAY (FastAPI)                      │
│  /api/query    /api/index    /api/crawl    /api/explain      │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────────────┐
│ RAG Engine   │ │ Crawler  │ │ TechDocGen Core  │
│              │ │ Engine   │ │ (Existing)       │
│ - Retriever  │ │          │ │                  │
│ - Reranker   │ │ - .sln   │ │ - Parsers        │
│ - Generator  │ │ - .csproj│ │ - LLM Enrichment │
│              │ │ - deps   │ │ - Analyzers      │
│              │ │ - sched  │ │ - Diagrams       │
└──────┬───────┘ │ - UI     │ └────────┬─────────┘
       │         └────┬─────┘          │
       ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                  KNOWLEDGE STORE                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ ChromaDB     │  │ SQLite       │  │ File Store        │  │
│  │ (Vectors)    │  │ (Metadata)   │  │ (Docs/Diagrams)   │  │
│  └──────────────┘  └──────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Feature Specifications

### PHASE 1: Knowledge Store & RAG Engine (Weeks 1-4)

---

#### F1.1 — Vector Knowledge Store

**Goal**: Store all TechDocGen-generated documentation as embeddings for semantic retrieval.

**Implementation Instructions (for Cursor/Claude Code):**

```
TASK: Create src/knowledge/vector_store.py

CONTEXT:
- TechDocGen generates markdown documentation per file/service
- Each document contains: overview, architecture, components, flows, dependencies
- We need to chunk these documents and store as vectors

REQUIREMENTS:
1. Use ChromaDB (runs locally, no external dependencies, supports air-gapped)
2. Use sentence-transformers for embeddings (all-MiniLM-L6-v2 for air-gapped, or Ollama embeddings)
3. Implement chunking strategy:
   - Split by markdown headers (##, ###) as natural boundaries
   - Each chunk gets metadata: source_file, service_name, probis_domain,
     chunk_type (overview|architecture|component|flow|dependency|diagram),
     language, last_updated, git_commit_hash
   - Max chunk size: 1500 tokens, overlap: 200 tokens
4. Support incremental updates (only re-embed changed documents)
5. Persist ChromaDB to: ./knowledge_base/chroma/
6. Persist metadata index to: ./knowledge_base/metadata.db (SQLite)

INTERFACE:
class VectorKnowledgeStore:
    def __init__(self, persist_dir: str, embedding_model: str)
    def ingest_document(self, doc_path: str, metadata: dict) -> int  # returns chunk count
    def ingest_batch(self, docs: list[tuple[str, dict]]) -> dict  # batch ingest
    def query(self, question: str, top_k: int = 10, filters: dict = None) -> list[ChunkResult]
    def delete_document(self, doc_path: str) -> bool
    def get_stats(self) -> dict  # total docs, chunks, last updated
    def rebuild_index(self) -> None  # full re-index

DEPENDENCIES TO ADD TO requirements.txt:
  chromadb>=0.4.22
  sentence-transformers>=2.2.2  # or use ollama embeddings
  tiktoken>=0.5.0  # for token counting

TESTS:
- Test chunking produces correct boundaries on sample markdown
- Test metadata filtering (by service, by probis, by chunk_type)
- Test incremental update only re-embeds changed files
- Test query returns relevant results for known questions
```

---

#### F1.2 — RAG Query Engine

**Goal**: Answer natural-language questions using retrieved context + LLM generation.

```
TASK: Create src/rag/query_engine.py

CONTEXT:
- VectorKnowledgeStore provides semantic retrieval
- Existing LLM providers (Ollama/MCP) handle generation
- Must support follow-up questions (conversation memory)

REQUIREMENTS:
1. Implement RAG pipeline: Query → Retrieve → Rerank → Augment → Generate
2. Retrieval: top_k=20 from ChromaDB, then rerank to top_k=5
3. Reranking: Use cross-encoder (cross-encoder/ms-marco-MiniLM-L-6-v2)
   or simple BM25 + vector score fusion for air-gapped
4. Prompt template for generation:

   SYSTEM: You are a CoreTax technical assistant. Answer questions about
   the CoreTax system architecture, code, and business logic using ONLY
   the provided context. If the context doesn't contain enough information,
   say so. Always cite the source file/service.

   CONTEXT:
   {retrieved_chunks_with_metadata}

   CONVERSATION HISTORY:
   {last_3_exchanges}

   USER QUESTION: {question}

5. Response format includes:
   - Answer text
   - Source references (file paths, service names)
   - Confidence indicator (high/medium/low based on retrieval scores)
   - Related topics for follow-up
6. Support query modes:
   - "explain" — detailed explanation with diagrams
   - "find" — locate components, files, patterns
   - "trace" — trace a flow from trigger to completion
   - "impact" — what would be affected by a change
   - "test" — suggest test cases for a component

INTERFACE:
class RAGQueryEngine:
    def __init__(self, store: VectorKnowledgeStore, llm_provider: BaseLLM)
    def query(self, question: str, mode: str = "explain",
              filters: dict = None, conversation_id: str = None) -> RAGResponse
    def trace_flow(self, entry_point: str) -> FlowTrace
    def impact_analysis(self, component: str) -> ImpactReport
    def suggest_tests(self, component: str) -> list[TestSuggestion]

TESTS:
- Test retrieval returns relevant chunks for architecture questions
- Test conversation memory maintains context across exchanges
- Test trace_flow produces correct sequence for known CQRS command
- Test impact_analysis identifies downstream dependencies
```

---

#### F1.3 — Documentation-to-Knowledge Pipeline

**Goal**: Automatically ingest TechDocGen output into the knowledge store.

```
TASK: Modify src/generator.py to add post-generation knowledge ingestion

CONTEXT:
- generator.py is the main orchestrator
- After generating markdown/PDF, we need to feed into VectorKnowledgeStore
- Must be opt-in via config (knowledge_store.enabled: true)

REQUIREMENTS:
1. After DocumentationGenerator produces output, call VectorKnowledgeStore.ingest_document()
2. Extract rich metadata from the generation context:
   - probis_domain (from domain profile config)
   - services discovered (from solution_discovery)
   - dependency_map (from DependencyAnalyzer)
   - message_flows (from flow extractors)
   - endpoints (from ServiceCatalog)
3. Also ingest structured data as separate knowledge types:
   - Dependency graph → "dependency" chunks
   - Service catalog → "endpoint" chunks
   - DDD documentation → "domain_model" chunks
   - Sequence diagrams → "flow" chunks (store mermaid source + description)
4. Add to config.yaml:

   knowledge_store:
     enabled: true
     persist_dir: "./knowledge_base"
     embedding_model: "all-MiniLM-L6-v2"  # or "ollama:nomic-embed-text"
     auto_ingest: true  # ingest after every generation
     chunk_strategy: "markdown_headers"  # or "fixed_size"

5. Add CLI command: techdocgen knowledge --rebuild
6. Add Streamlit UI section for knowledge store management

TESTS:
- Test full pipeline: parse → generate → ingest → query works end-to-end
- Test incremental: re-scan changed service only updates its chunks
```

---

### PHASE 2: Solution Crawler & Deep Analysis (Weeks 5-8)

---

#### F2.1 — Solution Crawler Engine

**Goal**: Automatically discover all components, dependencies, schedulers, and integrations from .sln files.

```
TASK: Create src/crawler/solution_crawler.py

CONTEXT:
- Existing solution_parser.py parses .sln → project references
- Existing csharp_project_parser.py parses .csproj → NuGet dependencies
- Need to go much deeper: scheduled jobs, DI registrations, middleware, API routes

REQUIREMENTS:
1. Starting from a .sln file, recursively discover:

   a. PROJECT STRUCTURE:
      - All .csproj projects with their layer classification
        (Domain, Application, Infrastructure, Presentation, Tests, Shared)
      - Inter-project references (build dependency graph)
      - NuGet package dependencies with versions
      - Framework targets (.NET version)

   b. RUNTIME COMPONENTS:
      - Controllers & API endpoints (HTTP method, route, auth attributes)
      - MassTransit consumers, sagas, state machines
      - Hangfire/Quartz scheduled jobs (cron expressions, job types)
      - Background services (IHostedService implementations)
      - gRPC services and protobuf definitions

   c. DATA LAYER:
      - EF Core DbContext definitions
      - Entity configurations & relationships
      - Database migrations history
      - Repository implementations

   d. INTEGRATION POINTS:
      - RabbitMQ exchanges, queues, bindings (from MassTransit config)
      - HTTP client registrations (external service calls)
      - Redis cache usage patterns
      - Consul service registration
      - S3/object storage usage

   e. UI COMPONENTS (Angular):
      - Module structure & lazy-loaded routes
      - Component hierarchy
      - Service injections & API calls
      - State management (NgRx stores/effects)
      - Shared component library usage

   f. CONFIGURATION:
      - appsettings.json structure
      - Environment-specific overrides
      - Feature flags
      - Connection strings (sanitized)

2. Output a unified CrawlReport as JSON:

   {
     "solution": "CoreTax.sln",
     "crawled_at": "ISO timestamp",
     "projects": [...],
     "dependency_graph": {...},
     "endpoints": [...],
     "consumers": [...],
     "schedulers": [...],
     "integrations": [...],
     "ui_components": [...],
     "data_models": [...],
     "configuration": {...}
   }

3. Store CrawlReport in knowledge store as structured chunks

INTERFACE:
class SolutionCrawler:
    def __init__(self, config: Config)
    def crawl(self, sln_path: str) -> CrawlReport
    def crawl_project(self, csproj_path: str) -> ProjectReport
    def discover_schedulers(self, project_path: str) -> list[SchedulerInfo]
    def discover_integrations(self, project_path: str) -> list[IntegrationPoint]
    def discover_ui_components(self, angular_path: str) -> list[UIComponent]
    def export_report(self, report: CrawlReport, format: str) -> str

DEPENDENCIES:
  # No new deps — uses existing parsers + regex extraction

TESTS:
- Test .sln parsing discovers all projects from examples/dotnet-cqrs-master/
- Test scheduler discovery finds Hangfire jobs with correct cron
- Test integration discovery finds RabbitMQ consumers
- Test UI component discovery finds Angular modules and routes
```

---

#### F2.2 — Flow Explainer

**Goal**: Trace and explain any business flow end-to-end with natural language.

```
TASK: Create src/crawler/flow_explainer.py

CONTEXT:
- Existing service_catalog.py extracts controllers & endpoints
- Existing flow_extractors/ extract messaging patterns
- Existing call_graph_analyzer.py traces intra-class calls
- Need to CONNECT these into end-to-end flow explanations

REQUIREMENTS:
1. Given a starting point (controller action, command, event), trace:
   - HTTP request → Controller → Command/Query Handler
   - Handler → Domain logic → Repository → Database
   - Handler → Publish event → RabbitMQ → Consumer(s)
   - Consumer → Further processing → Response
2. Generate both:
   - Mermaid sequence diagram (visual)
   - Natural language explanation (LLM-enriched)
   - Code references (file:line for each step)
3. Support cross-service flow tracing via message contracts
4. Identify: validation points, error handling, transaction boundaries

INTERFACE:
class FlowExplainer:
    def __init__(self, crawl_report: CrawlReport, llm: BaseLLM)
    def explain_flow(self, entry_point: str) -> FlowExplanation
    def explain_component(self, component_name: str) -> ComponentExplanation
    def explain_logic(self, file_path: str, method_name: str) -> LogicExplanation
    def generate_sequence_diagram(self, flow: FlowExplanation) -> str  # mermaid

OUTPUT EXAMPLE for explain_flow("POST /api/invoice/submit"):
  {
    "title": "Invoice Submission Flow",
    "steps": [
      {"order": 1, "component": "InvoiceController.Submit()",
       "file": "src/Presentation/Controllers/InvoiceController.cs:45",
       "action": "Receives HTTP POST, validates request model",
       "type": "http_entry"},
      {"order": 2, "component": "SubmitInvoiceCommand",
       "file": "src/Application/Commands/SubmitInvoiceCommand.cs:12",
       "action": "Creates command with invoice data, sends to MediatR pipeline",
       "type": "command"},
      ...
    ],
    "diagram": "sequenceDiagram\n  Client->>InvoiceController: POST /api/invoice/submit\n  ...",
    "explanation": "The invoice submission process begins when..."
  }
```

---

#### F2.3 — Logic & UI Component Explainer

**Goal**: Explain business logic and UI component behavior in natural language.

```
TASK: Create src/crawler/component_explainer.py

REQUIREMENTS:
1. For C# backend components:
   - Extract method body, analyze control flow (if/else, switch, loops)
   - Identify business rules and validation logic
   - Map domain events published/consumed
   - Explain in natural language using LLM
2. For Angular UI components:
   - Extract template structure (HTML)
   - Identify data bindings, event handlers, pipes
   - Map API calls made by the component's service
   - Explain user interaction flow
3. Store explanations in knowledge store for RAG retrieval

INTERFACE:
class ComponentExplainer:
    def __init__(self, llm: BaseLLM, store: VectorKnowledgeStore)
    def explain_class(self, file_path: str, class_name: str) -> ClassExplanation
    def explain_method(self, file_path: str, method_name: str) -> MethodExplanation
    def explain_ui_component(self, component_dir: str) -> UIComponentExplanation
    def explain_validation_rules(self, handler_path: str) -> list[ValidationRule]
```

---

### PHASE 3: IDE Integration (Weeks 9-12)

---

#### F3.1 — VS Code Extension

**Goal**: Bring RAG query capabilities directly into VS Code.

```
TASK: Create vscode-extension/ directory with VS Code extension

TECH STACK:
- TypeScript for extension
- VS Code Extension API
- WebSocket/HTTP client to TechDocGen API server

FEATURES:
1. CHAT PANEL (Side Panel):
   - Natural language query interface
   - Conversation history with follow-ups
   - Code block rendering with syntax highlighting
   - Mermaid diagram rendering
   - "Copy to editor" for generated code snippets
   - Source file links (click to open in editor)

2. CONTEXT MENU ACTIONS (Right-click on code):
   - "Explain This Code" → Sends selected code + file context to RAG
   - "Trace This Flow" → Starts from selected method, traces full flow
   - "Find Usages Across Services" → Cross-service dependency lookup
   - "What Tests Should Cover This?" → AI test case suggestions
   - "Impact Analysis" → What breaks if this changes

3. INLINE DOCUMENTATION (Hover):
   - Hover over class/method → Show RAG-enriched documentation
   - Show cross-service dependencies inline
   - Show message contracts for consumers/publishers

4. COMMAND PALETTE:
   - "TechDocGen: Index Current Workspace"
   - "TechDocGen: Rebuild Knowledge Base"
   - "TechDocGen: Explain Current File"
   - "TechDocGen: Show Architecture Diagram"
   - "TechDocGen: Find Component"
   - "TechDocGen: Trace Flow From Here"

5. STATUS BAR:
   - Knowledge base status (connected/indexing/error)
   - Last indexed timestamp
   - Quick query shortcut

EXTENSION STRUCTURE:
  vscode-extension/
  ├── package.json          # Extension manifest
  ├── tsconfig.json
  ├── src/
  │   ├── extension.ts      # Activation & command registration
  │   ├── api/
  │   │   └── client.ts     # HTTP/WebSocket client to TechDocGen API
  │   ├── providers/
  │   │   ├── chatProvider.ts       # WebView panel for chat
  │   │   ├── hoverProvider.ts      # Inline documentation
  │   │   ├── codeLensProvider.ts   # Inline action buttons
  │   │   └── treeProvider.ts       # Knowledge base explorer
  │   ├── commands/
  │   │   ├── explainCode.ts
  │   │   ├── traceFlow.ts
  │   │   ├── impactAnalysis.ts
  │   │   └── indexWorkspace.ts
  │   └── views/
  │       ├── chat.html             # Chat panel WebView
  │       └── diagram.html          # Mermaid diagram viewer
  └── README.md

CONFIGURATION (settings.json):
  {
    "techdocgen.serverUrl": "http://localhost:8080",
    "techdocgen.autoIndex": true,
    "techdocgen.hoverDocs": true,
    "techdocgen.inlineHints": true
  }
```

---

#### F3.2 — Visual Studio Extension (.sln Integration)

**Goal**: Deep integration with Visual Studio for .NET/CoreTax development.

```
TASK: Create vs-extension/ directory with Visual Studio 2022 extension (VSIX)

TECH STACK:
- C# for extension
- Visual Studio SDK (VSSDK)
- MEF for composition

FEATURES (same as VS Code plus):
1. SOLUTION EXPLORER INTEGRATION:
   - Right-click .sln → "Crawl & Index Solution"
   - Right-click .csproj → "Analyze Project Dependencies"
   - Overlay icons showing indexed/stale status

2. TOOL WINDOW:
   - Dedicated "TechDocGen Knowledge" tool window
   - Browse knowledge by: Service, Probis Domain, Component Type
   - Search across all indexed knowledge
   - View dependency graphs inline

3. EDITOR INTEGRATION:
   - CodeLens above classes/methods: "📖 Explain" | "🔗 Dependencies" | "🧪 Tests"
   - Quick Info (hover) enriched with RAG context
   - Light bulb actions: "Generate Documentation for This"

4. ARCHITECTURE DIAGRAM VIEW:
   - Custom diagram tool window
   - Interactive Mermaid/D3.js rendering
   - Click nodes to navigate to source code

EXTENSION STRUCTURE:
  vs-extension/
  ├── TechDocGen.VS.sln
  ├── src/
  │   ├── TechDocGen.VS/
  │   │   ├── TechDocGenPackage.cs      # VSIX package entry
  │   │   ├── Commands/
  │   │   │   ├── CrawlSolutionCommand.cs
  │   │   │   ├── ExplainCodeCommand.cs
  │   │   │   └── TraceFlowCommand.cs
  │   │   ├── ToolWindows/
  │   │   │   ├── KnowledgeBrowserWindow.cs
  │   │   │   └── DiagramViewerWindow.cs
  │   │   ├── Providers/
  │   │   │   ├── CodeLensProvider.cs
  │   │   │   └── QuickInfoProvider.cs
  │   │   └── Services/
  │   │       └── TechDocGenApiClient.cs
  │   └── TechDocGen.VS.vsixmanifest
  └── README.md
```

---

#### F3.3 — API Server

**Goal**: HTTP API server that IDE extensions connect to.

```
TASK: Create src/api/server.py using FastAPI

REQUIREMENTS:
1. RESTful API + WebSocket for streaming responses
2. Runs alongside Streamlit UI (different port)
3. Endpoints:

   POST /api/query
   Body: { "question": str, "mode": str, "filters": dict, "conversation_id": str }
   Response: { "answer": str, "sources": list, "confidence": str, "diagram": str? }

   POST /api/crawl
   Body: { "sln_path": str, "options": dict }
   Response: { "job_id": str, "status": "started" }

   GET /api/crawl/{job_id}/status
   Response: { "status": str, "progress": float, "files_processed": int }

   POST /api/explain
   Body: { "file_path": str, "component": str, "method": str? }
   Response: { "explanation": str, "diagram": str?, "references": list }

   POST /api/trace
   Body: { "entry_point": str, "depth": int }
   Response: { "flow": FlowExplanation, "diagram": str }

   POST /api/impact
   Body: { "component": str }
   Response: { "affected": list, "risk_level": str, "diagram": str }

   GET /api/knowledge/stats
   Response: { "total_docs": int, "total_chunks": int, "services": list, ... }

   POST /api/knowledge/rebuild
   Response: { "job_id": str, "status": "started" }

   WS /ws/query  # Streaming query responses
   WS /ws/index  # Real-time indexing progress

DEPENDENCIES:
  fastapi>=0.104.0
  uvicorn>=0.24.0
  websockets>=12.0

TESTS:
- Test all endpoints return correct response format
- Test WebSocket streaming delivers chunks progressively
- Test concurrent queries don't interfere
```

---

### PHASE 4: SDLC Acceleration Features (Weeks 13-16)

---

#### F4.1 — Bug Resolution Assistant

```
TASK: Create src/sdlc/bug_assistant.py

REQUIREMENTS:
1. Input: Bug description (natural language) or error stack trace
2. Process:
   a. Parse stack trace → identify affected files/methods
   b. RAG query for related components and flows
   c. Trace the affected flow end-to-end
   d. Identify related code changes (git log correlation)
   e. Suggest probable root causes ranked by likelihood
   f. Suggest fix approaches with code references
3. Output:
   - Root cause analysis with confidence scores
   - Affected component map
   - Suggested fix steps with code locations
   - Related past fixes (if git history available)
   - Test cases to verify the fix

INTERFACE:
class BugAssistant:
    def __init__(self, rag: RAGQueryEngine, crawler: SolutionCrawler)
    def analyze_bug(self, description: str, stack_trace: str = None) -> BugAnalysis
    def suggest_fix(self, analysis: BugAnalysis) -> list[FixSuggestion]
    def generate_test_cases(self, analysis: BugAnalysis) -> list[TestCase]
```

---

#### F4.2 — Test Case Generator

```
TASK: Create src/sdlc/test_generator.py

REQUIREMENTS:
1. Given a component (handler, controller, service), generate:
   - Unit test skeletons with meaningful test names
   - Edge cases based on validation logic analysis
   - Integration test scenarios for cross-service flows
   - Test data suggestions based on domain model constraints
2. Output format: xUnit (C#) test files ready to compile
3. Use RAG to understand component behavior before generating

INTERFACE:
class TestCaseGenerator:
    def __init__(self, rag: RAGQueryEngine, llm: BaseLLM)
    def generate_unit_tests(self, component_path: str) -> str  # C# test file content
    def generate_integration_tests(self, flow_name: str) -> str
    def suggest_edge_cases(self, handler_path: str) -> list[EdgeCase]
```

---

#### F4.3 — Architecture Validator

```
TASK: Create src/sdlc/architecture_validator.py

REQUIREMENTS:
1. Define architecture rules in YAML:
   - Layer dependency rules (Domain must not reference Infrastructure)
   - Naming conventions per layer
   - Required patterns per project type (e.g., Commands must have Validators)
   - Maximum coupling thresholds
2. Validate crawled solution against rules
3. Report violations with severity and suggested fixes

INTERFACE:
class ArchitectureValidator:
    def __init__(self, rules_path: str, crawl_report: CrawlReport)
    def validate(self) -> ValidationReport
    def check_layer_dependencies(self) -> list[Violation]
    def check_naming_conventions(self) -> list[Violation]
    def check_pattern_compliance(self) -> list[Violation]
```

---

## 7. Data Model

```
TASK: Create src/models/ with these Pydantic models

# src/models/knowledge.py
class ChunkResult:
    content: str
    metadata: ChunkMetadata
    score: float
    source_file: str

class ChunkMetadata:
    service_name: str
    probis_domain: str
    chunk_type: str  # overview|architecture|component|flow|dependency|endpoint|domain_model
    language: str
    git_commit: str
    last_updated: datetime

class RAGResponse:
    answer: str
    sources: list[SourceReference]
    confidence: str  # high|medium|low
    related_topics: list[str]
    diagram: str | None  # mermaid source
    mode: str

# src/models/crawler.py
class CrawlReport:
    solution: str
    crawled_at: datetime
    projects: list[ProjectInfo]
    dependency_graph: dict
    endpoints: list[EndpointInfo]
    consumers: list[ConsumerInfo]
    schedulers: list[SchedulerInfo]
    integrations: list[IntegrationPoint]
    ui_components: list[UIComponent]
    data_models: list[DataModel]

class ProjectInfo:
    name: str
    path: str
    layer: str
    framework: str
    references: list[str]
    nuget_packages: list[PackageRef]

class EndpointInfo:
    route: str
    method: str
    controller: str
    file: str
    line: int
    auth_required: bool
    request_model: str
    response_model: str

class SchedulerInfo:
    job_name: str
    cron_expression: str
    handler_class: str
    file: str
    description: str

class IntegrationPoint:
    type: str  # rabbitmq|http|redis|grpc|consul
    source_service: str
    target: str
    contract: str
    file: str

# src/models/flow.py
class FlowExplanation:
    title: str
    steps: list[FlowStep]
    diagram: str
    explanation: str
    entry_point: str

class FlowStep:
    order: int
    component: str
    file: str
    line: int
    action: str
    type: str  # http_entry|command|handler|domain_logic|repository|event|consumer

# src/models/sdlc.py
class BugAnalysis:
    summary: str
    affected_components: list[str]
    probable_causes: list[ProbableCause]
    affected_flow: FlowExplanation
    severity: str

class TestCase:
    name: str
    description: str
    type: str  # unit|integration|edge_case
    code: str  # C# test code
    component_under_test: str
```

---

## 8. Configuration Extension

```yaml
# Additions to config.yaml

# === RAG Knowledge Store ===
knowledge_store:
  enabled: true
  persist_dir: "./knowledge_base"
  embedding:
    provider: "ollama"           # ollama | sentence-transformers
    model: "nomic-embed-text"    # or "all-MiniLM-L6-v2"
    batch_size: 32
  chunking:
    strategy: "markdown_headers"  # markdown_headers | fixed_size | semantic
    max_tokens: 1500
    overlap_tokens: 200
  reranker:
    enabled: true
    model: "bm25_vector_fusion"   # bm25_vector_fusion | cross_encoder
  auto_ingest: true

# === Solution Crawler ===
crawler:
  solution_paths:                 # List of .sln files to crawl
    - "/path/to/CoreTax.sln"
  angular_paths:                  # Frontend roots
    - "/path/to/CoreTax.Web/ClientApp"
  scan_depth: 10                  # Max directory depth
  include_tests: false            # Include test projects
  scheduler_patterns:
    - "Hangfire"
    - "Quartz"
    - "IHostedService"
  crawl_schedule: "daily"         # daily | on_change | manual

# === API Server ===
api:
  host: "0.0.0.0"
  port: 8080
  cors_origins: ["http://localhost:*"]
  auth:
    enabled: false                # Enable for multi-user
    type: "api_key"
  websocket:
    enabled: true
    max_connections: 50

# === IDE Integration ===
ide:
  vscode:
    hover_docs: true
    code_lens: true
    auto_index: true
  visual_studio:
    solution_explorer_integration: true
    code_lens: true
```

---

## 9. Project Structure (Final)

```
TechDocGen/
├── app.py                          # Existing Streamlit UI (enhanced)
├── config.yaml                     # Extended configuration
├── requirements.txt                # Updated dependencies
├── src/
│   ├── __init__.py
│   ├── generator.py                # Modified: post-generation ingestion
│   ├── config.py                   # Existing
│   ├── models/                     # NEW: Pydantic data models
│   │   ├── __init__.py
│   │   ├── knowledge.py
│   │   ├── crawler.py
│   │   ├── flow.py
│   │   └── sdlc.py
│   ├── knowledge/                  # NEW: Vector store & RAG
│   │   ├── __init__.py
│   │   ├── vector_store.py         # F1.1
│   │   ├── chunker.py             # Document chunking strategies
│   │   └── embeddings.py          # Embedding provider abstraction
│   ├── rag/                        # NEW: RAG query engine
│   │   ├── __init__.py
│   │   ├── query_engine.py         # F1.2
│   │   ├── reranker.py            # Result reranking
│   │   └── prompts.py             # RAG prompt templates
│   ├── crawler/                    # NEW: Solution crawler
│   │   ├── __init__.py
│   │   ├── solution_crawler.py     # F2.1
│   │   ├── flow_explainer.py       # F2.2
│   │   ├── component_explainer.py  # F2.3
│   │   ├── scheduler_discovery.py  # Hangfire/Quartz extraction
│   │   ├── integration_discovery.py # Integration point detection
│   │   └── ui_crawler.py          # Angular component crawler
│   ├── api/                        # NEW: API server
│   │   ├── __init__.py
│   │   ├── server.py               # F3.3 FastAPI server
│   │   ├── routes/
│   │   │   ├── query.py
│   │   │   ├── crawl.py
│   │   │   ├── explain.py
│   │   │   └── knowledge.py
│   │   └── websocket.py
│   ├── sdlc/                       # NEW: SDLC acceleration
│   │   ├── __init__.py
│   │   ├── bug_assistant.py        # F4.1
│   │   ├── test_generator.py       # F4.2
│   │   └── architecture_validator.py # F4.3
│   ├── parsers/                    # Existing (unchanged)
│   ├── readers/                    # Existing (unchanged)
│   ├── llm/                        # Existing (enhanced with embedding support)
│   ├── flow_extractors/            # Existing (unchanged)
│   └── *.py                        # Other existing modules
├── vscode-extension/               # NEW: VS Code extension
│   ├── package.json
│   ├── src/
│   └── README.md
├── vs-extension/                   # NEW: Visual Studio extension
│   ├── TechDocGen.VS.sln
│   ├── src/
│   └── README.md
├── knowledge_base/                 # NEW: Persisted knowledge (gitignored)
│   ├── chroma/
│   └── metadata.db
├── tests/                          # NEW: Comprehensive test suite
│   ├── test_vector_store.py
│   ├── test_rag_engine.py
│   ├── test_crawler.py
│   ├── test_flow_explainer.py
│   ├── test_api.py
│   └── test_sdlc.py
└── architecture_rules/             # NEW: Architecture validation rules
    └── coretax_rules.yaml
```

---

## 10. Implementation Priority & Dependencies

```
PHASE 1 (Weeks 1-4): Foundation
  F1.1 Vector Store ──► F1.2 RAG Engine ──► F1.3 Pipeline Integration
  [No external deps]    [Depends on F1.1]   [Depends on F1.1 + F1.2]

PHASE 2 (Weeks 5-8): Intelligence
  F2.1 Solution Crawler ──► F2.2 Flow Explainer ──► F2.3 Component Explainer
  [Independent]             [Depends on F2.1]       [Depends on F2.1 + F1.2]

PHASE 3 (Weeks 9-12): IDE Integration
  F3.3 API Server ──► F3.1 VS Code Extension ──► F3.2 Visual Studio Extension
  [Depends on F1.2]   [Depends on F3.3]          [Depends on F3.3]

PHASE 4 (Weeks 13-16): SDLC Features
  F4.1 Bug Assistant ──► F4.2 Test Generator ──► F4.3 Architecture Validator
  [Depends on F1.2+F2.1] [Depends on F1.2+F2.1]  [Depends on F2.1]
```

---

## 11. Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| Developer onboarding time | 3 months | < 2 weeks |
| Average bug resolution time | 4-8 hours | < 1 hour |
| Architecture question response | Ask senior dev (hours) | Instant (RAG) |
| Test case coverage for new features | Manual (60%) | AI-assisted (85%) |
| Documentation freshness | Stale (quarterly) | Always current |
| Cross-service flow understanding | Code reading (days) | One query (seconds) |

---

## 12. Technical Constraints (Air-Gapped)

All components must operate without internet:

- **Embeddings**: Ollama `nomic-embed-text` or pre-downloaded sentence-transformers model
- **Vector DB**: ChromaDB (local SQLite + DuckDB backend, no cloud)
- **LLM**: Ollama with DeepSeek-Coder-V2 (already deployed)
- **Reranker**: BM25 + vector score fusion (no cloud cross-encoder needed)
- **IDE Extensions**: Packaged as .vsix files, no marketplace dependency
- **All Python deps**: Pre-downloaded wheels in offline PyPI mirror

---

## 13. Execution Commands

```bash
# Start knowledge-enhanced TechDocGen
python app.py  # Streamlit UI on :8501

# Start API server for IDE integration
python -m src.api.server  # FastAPI on :8080

# CLI commands
python -m techdocgen crawl --sln /path/to/CoreTax.sln
python -m techdocgen index --rebuild
python -m techdocgen query "How does invoice submission work?"
python -m techdocgen trace "InvoiceController.Submit"
python -m techdocgen impact "TaxPayer aggregate"
python -m techdocgen test-gen --component "SubmitInvoiceHandler"
python -m techdocgen validate --rules architecture_rules/coretax_rules.yaml
```

---

*This PRD is designed to be fed directly into Cursor or Claude Code. Each feature specification (F1.1 through F4.3) contains the complete context, interface definitions, and test requirements needed for an AI coding assistant to implement the feature autonomously. Start with Phase 1, validate, then proceed sequentially.*
