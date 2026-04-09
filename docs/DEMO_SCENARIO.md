# Lumen.AI Demo Scenario & Narration Guide

> **Lumen.AI | SDLC Knowledge Engine**
> RAG-Powered Technical Documentation & Code Intelligence
>
> _Formerly Neo-TDG. The brand changed; the engine got deeper._

---

## Table of Contents

1. [Demo Overview](#1-demo-overview)
2. [Pre-Demo Setup](#2-pre-demo-setup)
3. [Demo Scenario 1: Application Initialization](#3-demo-scenario-1-application-initialization)
4. [Demo Scenario 2: Solution Crawler](#4-demo-scenario-2-solution-crawler)
5. [Demo Scenario 3: Document Generation & Download](#5-demo-scenario-3-document-generation--download)
6. [Demo Scenario 4: Knowledge Store Ingestion](#6-demo-scenario-4-knowledge-store-ingestion)
7. [Demo Scenario 5: RAG Knowledge Chat](#7-demo-scenario-5-rag-knowledge-chat)
8. [Demo Scenario 6: Flow Explorer](#8-demo-scenario-6-flow-explorer)
9. [Demo Scenario 7: SDLC Tools - Bug Resolution](#9-demo-scenario-7-sdlc-tools---bug-resolution)
10. [Demo Scenario 8: SDLC Tools - Test Generator](#10-demo-scenario-8-sdlc-tools---test-generator)
11. [Demo Scenario 9: SDLC Tools - Architecture Validator](#11-demo-scenario-9-sdlc-tools---architecture-validator)
12. [Demo Scenario 10: End-to-End Workflow](#12-demo-scenario-10-end-to-end-workflow)
13. [Feature Summary Matrix](#13-feature-summary-matrix)

---

## 1. Demo Overview

### Purpose

Demonstrate how Lumen.AI accelerates the Software Development Life Cycle (SDLC) by providing AI-powered code intelligence, automated documentation, and developer productivity tools across both .NET back-end and Angular front-end codebases.

### Target Audience

- Development Team Leads
- Software Architects
- Project Managers
- QA Engineers
- DJP Technical Stakeholders

### Key Value Propositions

| Value | Description |
|-------|-------------|
| Automated Discovery | Crawl .NET solutions to discover architecture, endpoints, consumers, schedulers, and integrations automatically |
| Deep Code & Config Analysis | Extract DDD aggregates, domain events, DI registrations, appsettings keys, and cluster projects into business domains |
| Cross-Domain Contracts | Join named HTTP clients with config URLs to surface every cross-service runtime dependency |
| Front-End Coverage | Auto-discover Angular components, modules, routes, and wire each one to the back-end Controller it calls |
| Multi-Source Input | Crawl from a local path, an uploaded ZIP, or a GitHub repository — no manual checkout required |
| AI-Powered Knowledge | RAG-based chat understands your entire codebase and answers technical questions |
| Documentation Generation | Auto-generate comprehensive Markdown and PDF reports including sequence diagrams, dependency graphs, and UI→API wiring |
| Flow Tracing | Trace business flows end-to-end across microservices |
| SDLC Acceleration | Bug resolution, test generation, and architecture validation tools |

### Tech Stack Covered in Demo

- C# / .NET 8
- Angular (Frontend)
- CQRS with MediatR
- MassTransit + RabbitMQ (Message Bus)
- Redis (Distributed Cache)
- Hangfire (Background Jobs)
- Consul (Service Discovery)
- ELK Stack (Logging)
- AWS S3 (Object Storage)
- Entity Framework Core (ORM)

---

## 2. Pre-Demo Setup

### Prerequisites

| Item | Requirement |
|------|-------------|
| Ollama | Running locally with `deepseek-coder-v2:16b` and `nomic-embed-text` models pulled |
| Python | 3.9+ with all dependencies installed (`pip install -r requirements.txt`) |
| Browser | Chrome (latest) |
| Example Project | `examples/CoreTaxSample/` directory present |

### Startup Steps

1. **Start Ollama** (if not running):
   ```bash
   ollama serve
   ```

2. **Verify Models**:
   ```bash
   ollama list
   # Should show: deepseek-coder-v2:16b, nomic-embed-text
   ```

3. **Start Lumen.AI**:
   ```bash
   cd /Users/priyo/Downloads/DJP/Neo-TDG
   streamlit run app.py --server.port 8503
   ```

4. **Open Browser**: Navigate to `http://localhost:8503`

### Demo Environment Checklist

- [ ] Ollama is running and models are loaded
- [ ] Lumen.AI application is accessible at localhost:8503
- [ ] CoreTaxSample example project is present (with the Angular SPA next to the .sln if you want UI coverage)
- [ ] `crawler.deep_analysis.enabled: true` in `config.yaml` (default on this branch)
- [ ] Screen is shared/projected for audience

---

## 3. Demo Scenario 1: Application Initialization

### Objective
Show how Neo-TDG connects to the AI backend and initializes all services.

### Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open browser at `http://localhost:8503` | Lumen.AI landing page loads with the soft-blue IBM Carbon header — wordmark reads **Lumen.AI** and the subtitle is "SDLC Knowledge Engine — RAG-Powered Code Intelligence" |
| 2 | Observe the top navigation order | Tabs in order: **Solution Crawler → Knowledge Store → RAG Chat → Flow Explorer → SDLC Tools** |
| 3 | Expand "Ollama Configuration" in the sidebar | Shows Ollama URL field (`http://localhost:11434`), LLM Model dropdown, and Embedding Model field |
| 4 | Select model `deepseek-coder-v2:16b` from dropdown | Model selection updates |
| 5 | Click "Initialize / Reconnect" button | Service initialization begins |
| 6 | Observe Service Status indicators | LLM indicator turns GREEN, Store indicator turns GREEN |

### Narration Script

> "Welcome to Lumen.AI, the SDLC Knowledge Engine. This tool leverages AI-powered RAG technology to provide deep code intelligence across an entire solution -- back-end and front-end together.
>
> Notice the IBM Carbon-inspired interface and the streamlined navigation: Solution Crawler is the entry point, then Knowledge Store, RAG Chat, Flow Explorer, and SDLC Tools.
>
> On the left sidebar, we configure the AI backend. We're using Ollama with the deepseek-coder model for code understanding, and nomic-embed-text for vector embeddings -- everything runs locally, fully air-gapped.
>
> When I click Initialize, the system connects to the LLM, sets up the vector knowledge store, and prepares all analysis engines. Notice both status indicators are now green -- we're ready to go."

---

## 4. Demo Scenario 2: Solution Crawler

### Objective
Demonstrate automated discovery of a .NET solution's architecture, endpoints, consumers, schedulers, integrations, data models, **and the Angular front-end that calls them**. Show that the crawler accepts three input sources: a local path, an uploaded ZIP, or a GitHub repository.

### Multi-Source Input

The Solution Crawler page now opens with **three tabs** above the path field, letting you point at a solution from any source:

| Source Tab | Use When | Notes |
|------------|----------|-------|
| **Local Path** | The solution lives on the same machine as Lumen.AI | Accepts a `.sln` path or a directory containing one (auto-discovered) |
| **Upload Solution (ZIP)** | A reviewer ships you a code drop, or you can't grant disk access to the host | Extract happens in a temp dir; the first `.sln` found inside is used |
| **GitHub Repository** | The solution lives in version control | Shallow clones (`--depth 1`) into a temp dir; supports an optional branch field |

Below the source tabs there is also an **Angular front-end path (optional)** field. Leave it blank and the crawler auto-detects any `angular.json` under the solution directory (skipping `node_modules`/`bin`/`obj`/`.git`). Provide an explicit path for monorepos that keep the SPA elsewhere.

### Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click "Solution Crawler" in Navigation | Solution Crawler page loads with three source tabs |
| 2 | Stay on the **Local Path** tab and enter `/Users/priyo/Downloads/DJP/Neo-TDG/examples/CoreTaxSample` | Path appears in text input |
| 3 | Leave the Angular path field blank | Auto-detect will pick up `CoreTax.Angular/` |
| 4 | Click "Crawl Solution" button | Progress bar advances, processing each project |
| 5 | Wait for crawl to complete | Success toast: "Crawled 8 projects, 19 endpoints, 6 consumers, 8 schedulers, N UI components" |
| 6 | Click "Projects" tab | Shows 8 projects classified into Domain, Application, Infrastructure, Presentation, Worker, Contracts, Shared, Angular |
| 7 | Scroll to Dependency Graph | Mermaid `graph LR` shows project-to-project references grouped by layer; cross-domain contracts overlay as dotted arrows |
| 8 | Click "Endpoints" tab | Lists all 19 API endpoints with HTTP method, route, controller, auth status |
| 9 | Click "Consumers" tab | Shows 6 MassTransit consumers (InvoiceApprovalSaga, AuditScheduledConsumer, etc.) |
| 10 | Click "Schedulers" tab | Shows 8 schedulers (Hangfire recurring jobs, background services, fire-and-forget) |
| 11 | Click "Integrations" tab | Shows 7 integrations grouped by type: Consul, gRPC, HTTP, RabbitMQ, Redis, S3 |
| 12 | Click "Data Models" tab | Shows 5 EF Core entities: Taxpayer, TaxInvoice, TaxReturn, TaxPayment, TaxAudit |

### Optional: Re-crawl from a GitHub Repository

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Switch to the **GitHub Repository** tab | URL + branch fields appear |
| 2 | Paste a repo URL (e.g. `https://github.com/owner/coretax-sample.git`) | URL captured |
| 3 | (Optional) enter a branch name | Branch captured |
| 4 | Click "Clone Repository" | Spinner; on success, "Cloned. Found solution: <name>.sln" |
| 5 | Click "Crawl Solution" | Same crawl pipeline runs against the cloned working tree |

### Narration Script

> "Now let's see the Solution Crawler in action. The first thing to notice is that the crawler accepts three input sources -- a local path, an uploaded ZIP, or a GitHub URL -- so reviewers and external auditors can run Lumen.AI without any disk-mount gymnastics.
>
> I'll stay on the local-path tab and point it at our CoreTaxSample solution -- a realistic .NET 8 solution simulating the Indonesian tax system with full microservice architecture and an Angular SPA shipped next to the .sln. I'm leaving the Angular path field blank because the crawler auto-detects `angular.json` under the solution directory.
>
> The crawler is now parsing the .sln file, discovering projects, analyzing each one, and -- in parallel -- crawling the Angular components, modules, and HTTP service calls. It's reading controllers for endpoints, scanning for MassTransit consumers, finding Hangfire jobs, detecting integrations with Redis, RabbitMQ, Consul, and more. With deep analysis turned on, it's also extracting DI registrations, appsettings keys, and DDD aggregates, then clustering everything into business domains.
>
> The results are impressive -- 8 projects, 19 API endpoints, 6 message consumers, 8 scheduled jobs, and the front-end components -- all discovered automatically. Let me walk through each tab.
>
> In Projects, we see the Clean Architecture layers clearly. The dependency graph shows how Presentation depends on Application, which depends on Domain -- exactly our intended architecture -- and any cross-domain runtime contracts overlay as dotted arrows on the same diagram.
>
> The Endpoints tab reveals all REST APIs -- notice the Auth indicators showing which endpoints require authorization. The /reports endpoints are public, while tax operations require authentication.
>
> The Consumers tab found our MassTransit event consumers including the InvoiceApprovalSaga -- a state machine for invoice processing workflows.
>
> Schedulers show Hangfire cron jobs like daily-tax-computation and monthly-compliance-report, plus background services for real-time processing.
>
> Integrations are grouped by type -- we can see connections to Redis for caching, RabbitMQ for messaging, Consul for service discovery, S3 for document storage, and HTTP clients for payment gateway integration.
>
> Finally, Data Models shows all 5 entities managed by our CoreTaxDbContext."

### Key Talking Points

- Automatic layer classification (Domain, Application, Infrastructure, Presentation)
- NuGet package detection with versions
- Auth requirement detection from `[Authorize]` attributes
- MassTransit Saga detection alongside standard consumers
- Multiple scheduler types: Hangfire recurring, fire-and-forget, delayed, BackgroundService, IHostedService

---

## 5. Demo Scenario 3: Document Generation & Download

### Objective
Show automatic documentation generation in Markdown and PDF formats with download capability. The generated doc covers **everything** the crawler discovered: back-end projects, deep code/config analysis, business domains, sequence flows, and the Angular front-end with its UI→API wiring.

### Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | After crawl completes, scroll to the download section | Two buttons appear: "Download MD Report" and "Download PDF Report" |
| 2 | Click "Download MD Report" | Browser downloads `CoreTaxSample_report.md` |
| 3 | Open the MD file | Full technical documentation with tables, architecture diagram, dependency graph (with contract overlay), per-domain sequence diagrams, configurations, DI registrations, code symbols, and the Angular UI section |
| 4 | Click "Download PDF Report" | Browser downloads `CoreTaxSample_report.pdf` |
| 5 | Open the PDF file | Same content rendered as a print-ready PDF — headings, tables, code blocks, all unicode arrows and em-dashes safely transliterated |

### Narration Script

> "One of the key features is automatic documentation generation. After every crawl, Lumen.AI generates comprehensive technical documentation in both Markdown and PDF.
>
> What you get is not just a list of files. The doc opens with a Solution Overview metrics table, then walks through the discovered Business Domains, the Cross-Domain Contracts that connect them, and a per-domain Sequence Flow diagram showing how Client → Controller → external services → message bus → consumers actually interact at runtime. Synchronous calls render as solid arrows; rabbitmq/kafka/queue calls render as dashed arrows.
>
> Then it covers the back-end internals: every project with framework and NuGet packages, all configuration keys extracted from `appsettings.*.json` and `launchSettings.json`, every DI registration discovered in `Startup.cs`/`Program.cs`, and every C# code symbol classified into DDD roles -- aggregate roots, domain events, value objects, repositories, controllers.
>
> Endpoints, consumers, schedulers, integrations, and data models are all there. Then comes the Angular Front-End section -- a per-module table of components with their selectors, routes, API calls, and source files, plus a UI → API Wiring Mermaid diagram that connects each component to the back-end Controller it calls. The doc closes with the Dependency Graph: a layered Mermaid view of project references with cross-domain runtime contracts overlaid as dotted edges, plus a textual edge table.
>
> The PDF version provides the same content in a print-ready format -- suitable for sharing with stakeholders who prefer traditional documents. Em-dashes, arrows, and other unicode characters are safely transliterated so the PDF generator never chokes.
>
> This eliminates hours of manual documentation work. Every time you crawl a solution, the docs are instantly up to date."

### MD/PDF Report Structure

The generated report includes these sections (in order):

1. **Title & Metadata** -- Solution name, crawl timestamp, Lumen.AI auto-gen tag
2. **Solution Overview** -- Metrics table including: projects, business domains, domain contracts, endpoints, consumers, schedulers, integrations, data models, **Angular UI components**, configuration keys, DI registrations, code symbols, frameworks; plus a Layer Distribution sub-table
3. **Business Domains** -- Per-domain card: projects, namespaces, aggregates, domain events, endpoints
4. **Domain Contracts** -- Cross-service contracts joined from DI registrations + configuration URLs (source domain → target service, transport, interface, config URL, registration site)
5. **Sequence Flows** -- One Mermaid `sequenceDiagram` per business domain showing Client → Controllers → external services → Bus/Consumers; solid arrows for sync, dashed for async transports
6. **Architecture Diagram** -- Mermaid `graph TD` grouping projects by layer
7. **Project Details** -- Each project with layer, framework, path, references, NuGet packages
8. **Configurations** -- Every key extracted from `appsettings.json` / `appsettings.{env}.json` / `launchSettings.json` / `*.config`, including environment-variable references
9. **DI Registrations** -- Every `AddSingleton`/`AddScoped`/`AddTransient`/`AddHttpClient`/`AddDbContext`/`AddMediatR` call site with service type, implementation, named client, file:line
10. **Code Symbols** -- C# classes/interfaces/records with DDD roles flagged: aggregate roots, domain events, value objects, repositories, controllers
11. **API Endpoints** -- Table with method, route, controller, auth status
12. **Message Consumers** -- Consumer class, message type, queue
13. **Scheduled Jobs** -- Job name, schedule/cron, description
14. **Integration Points** -- Grouped by type with source, target, contract
15. **Data Models** -- Entity name, DbContext, properties
16. **Angular Front-End** -- Per-module table of components (selector, routes, API calls, file) plus a `UI → API Wiring` Mermaid `graph LR` connecting each component to the back-end Controller it hits (suffix-matched against discovered endpoint routes; unmatched calls render as external leaves)
17. **Dependency Graph** -- Mermaid `graph LR` with layer subgraphs, project references as solid arrows, cross-domain contracts as dotted arrows with transport labels, plus a textual edge table

---

## 6. Demo Scenario 4: Knowledge Store Ingestion

### Objective
Show how crawl results are ingested into the RAG knowledge base for AI-powered querying.

### Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | On Solution Crawler page, click "Ingest to Knowledge Store" | Spinner shows "Ingesting crawl report..." |
| 2 | Wait for ingestion to complete | Success message: "Ingested crawl report: X chunks created" |
| 3 | Click "Knowledge Store" in Navigation | Knowledge Store page loads |
| 4 | Observe Statistics section | Shows total chunks, documents, and indexed services |
| 5 | Observe Chunk Type Distribution | Shows counts for: overview, architecture, component, flow, dependency, endpoint, domain_model |
| 6 | Scroll to Document Browser | Lists all ingested documents |

### Narration Script

> "Now let's make this crawl data queryable by AI. I'll click 'Ingest to Knowledge Store' -- this converts the crawl results into vector-embedded chunks that our RAG engine can search.
>
> The system created structured chunks for each aspect of the solution -- endpoints become endpoint chunks, consumers become component chunks, and the overall architecture becomes overview chunks.
>
> In the Knowledge Store page, we can see the statistics: total chunks stored, number of documents, and indexed services. The chunk type distribution shows how our knowledge is categorized.
>
> This is the foundation for AI-powered code intelligence -- the knowledge store is our codebase's memory."

### Additional Knowledge Store Features

| Feature | Description |
|---------|-------------|
| Markdown File Ingestion | Ingest individual .md files or entire directories |
| TechDocGen Output | Import pre-generated documentation from TechDocGen tool |
| Full Rebuild | Drop and rebuild the entire index from scratch |
| Document Browser | View and delete individual documents |
| Service Filtering | Filter chunks by service name |
| Probis Domain Filtering | Filter by business domain |

---

## 7. Demo Scenario 5: RAG Knowledge Chat

### Objective
Demonstrate AI-powered conversational querying of the codebase using different analysis modes.

### Sub-Scenario 5A: Explain Mode

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click "RAG Chat" in Navigation | RAG Knowledge Chat page loads |
| 2 | Select Query Mode: "explain" | Explain mode selected |
| 3 | Type: "How does the tax invoice submission process work?" | Question appears in chat input |
| 4 | Press Enter or click Send | AI generates detailed explanation with architecture context |
| 5 | Observe response | Explanation includes component names, flow description, source citations with relevance scores |

### Sub-Scenario 5B: Find Mode

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select Query Mode: "find" | Find mode selected |
| 2 | Type: "Where are the Redis caching implementations?" | Question submitted |
| 3 | Observe response | Lists file paths, class names, and relevant code patterns for Redis usage |

### Sub-Scenario 5C: Trace Mode

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select Query Mode: "trace" | Trace mode selected |
| 2 | Type: "Trace the payment processing flow from API to completion" | Question submitted |
| 3 | Observe response | Step-by-step flow from PaymentController through handler, domain logic, event publishing, to consumer processing |

### Sub-Scenario 5D: Impact Mode

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select Query Mode: "impact" | Impact mode selected |
| 2 | Type: "What would be affected if I change the Taxpayer entity?" | Question submitted |
| 3 | Observe response | Lists downstream dependencies: handlers, DTOs, controllers, consumers, and tests that would be impacted |

### Sub-Scenario 5E: Test Mode

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select Query Mode: "test" | Test mode selected |
| 2 | Type: "Suggest test cases for the InvoiceSubmittedConsumer" | Question submitted |
| 3 | Observe response | Lists unit tests, integration tests, and edge cases with C# xUnit test skeletons |

### Narration Script

> "This is where Neo-TDG truly shines -- the RAG Knowledge Chat. It understands our entire codebase and can answer technical questions in five specialized modes.
>
> In EXPLAIN mode, I'll ask about the invoice submission process. Notice how the AI provides a comprehensive answer referencing actual components -- InvoiceController, SubmitInvoiceCommandHandler, the domain entity, and the published event. Each source is cited with a relevance score.
>
> FIND mode is like a smart code search. When I ask for Redis implementations, it pinpoints the exact classes and files, not just keyword matches.
>
> TRACE mode is powerful for understanding flows. Watch how it traces the payment flow step by step -- from the API controller, through the command handler, into domain logic, repository persistence, event publishing, and finally the consumer that processes the payment confirmation.
>
> IMPACT mode helps with change planning. If we modify the Taxpayer entity, the AI identifies every downstream dependency -- handlers, DTOs, controllers, and test files that would need updating.
>
> TEST mode generates actual test code. For the InvoiceSubmittedConsumer, it suggests unit tests for happy path and error scenarios, integration tests with message bus, and edge cases like duplicate messages."

### Chat Features

| Feature | Description |
|---------|-------------|
| Conversation History | Persistent conversations with browse and reload |
| Metadata Filters | Filter by Service Name, Probis Domain, Chunk Type |
| Source Citations | Every answer shows source files with relevance scores |
| Confidence Badges | High (green), Medium (orange), Low (red) confidence indicators |
| Mermaid Diagrams | Sequence and flow diagrams rendered inline |
| Related Topics | Suggested follow-up questions |

---

## 8. Demo Scenario 6: Flow Explorer

### Objective
Demonstrate visual flow tracing and component explanation capabilities.

### Sub-Scenario 6A: Trace Flow

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click "Flow Explorer" in Navigation | Flow Explorer page loads with two tabs |
| 2 | Select "Trace Flow" tab | Flow tracing interface appears |
| 3 | Enter entry point: `POST /api/v1/invoices/submit` | Entry point entered |
| 4 | Click "Trace Flow" button | AI analyzes and generates flow |
| 5 | Observe Sequence Diagram | Mermaid sequence diagram shows interactions between Controller, Handler, Domain, Repository, EventBus, Consumer |
| 6 | Observe Step-by-Step breakdown | Each step shows: icon, component, action, file reference |

### Sub-Scenario 6B: Explain Component

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select "Explain Component" tab | Component explanation interface appears |
| 2 | Enter file path to a handler | File path entered |
| 3 | Select Explain Type: "Class" | Class explanation mode selected |
| 4 | Click "Explain" | AI generates class explanation |
| 5 | Observe output | Shows: purpose, constructor dependencies, domain events, business rules, dependency list |

### Sub-Scenario 6C: Validation Rules

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select Explain Type: "Validation Rules" | Validation mode selected |
| 2 | Enter path to a validator file | Path entered |
| 3 | Click "Explain" | Validation rules extracted |
| 4 | Observe output | Lists each rule: name, target field, condition, file location |

### Narration Script

> "The Flow Explorer provides visual tracing of business flows. Let me trace the invoice submission endpoint.
>
> Watch as Neo-TDG generates a sequence diagram showing the full flow -- from the HTTP request hitting InvoiceController, dispatching a SubmitInvoiceCommand via MediatR, the handler performing business logic, saving to the database via repository, publishing an InvoiceSubmittedEvent, and the consumer processing it asynchronously.
>
> Each step includes the actual file and line number -- you can click through to the source code.
>
> The Explain Component tab lets us deep-dive into any class. Here I can see the handler's purpose, its constructor dependencies injected via DI, what domain events it fires, and what business rules it enforces.
>
> The Validation Rules extractor pulls out FluentValidation rules showing exactly what constraints are applied to each field -- NPWP format validation, currency rules, date ranges, and more."

### Flow Step Icons

| Icon | Type | Description |
|------|------|-------------|
| `->` | HTTP Entry | Controller endpoint receiving the request |
| `>>` | Command | CQRS command dispatched |
| `**` | Handler | Command/Query handler processing |
| `~~` | Domain Logic | Business rule execution |
| `[]` | Repository | Database operation |
| `<>` | Event | Domain event published |
| `<<` | Consumer | Async event consumer processing |

---

## 9. Demo Scenario 7: SDLC Tools - Bug Resolution

### Objective
Show AI-powered bug analysis and resolution suggestions.

### Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click "SDLC Tools" in Navigation | SDLC Tools page loads with 3 tabs |
| 2 | Select "Bug Resolution" tab | Bug resolution interface appears |
| 3 | Enter bug description: "Tax return filing fails with NullReferenceException when taxpayer has no registered address. The SPT submission endpoint returns 500 error." | Bug description entered |
| 4 | Enter stack trace (optional): `System.NullReferenceException: Object reference not set to an instance...at CoreTax.Application.Handlers.FileTaxReturnHandler.Handle()` | Stack trace entered |
| 5 | Click "Analyze Bug" | AI analyzes bug against codebase knowledge |
| 6 | Observe Summary | Bug summary with severity level (e.g., "high") |
| 7 | Observe Affected Components | Lists impacted classes: FileTaxReturnHandler, TaxReturn entity, TaxReturnController |
| 8 | Observe Probable Causes | Ranked causes with confidence scores (e.g., "Missing null check on Taxpayer.Address - 0.85") |
| 9 | Observe Suggested Fixes | Fix descriptions with code location, suggested code change, and risk level |
| 10 | Expand "Verification Test Cases" | Shows C# xUnit test code to verify the fix |

### Narration Script

> "The Bug Resolution Assistant accelerates debugging. I'll describe a real scenario -- tax return filing fails when a taxpayer has no address.
>
> The AI analyzes this against our codebase knowledge and provides a structured response. It identifies the severity as HIGH because it affects a core business flow.
>
> It pinpoints the affected components -- the FileTaxReturnHandler, TaxReturn entity, and the controller.
>
> The probable causes are ranked by confidence. The top cause is a missing null check on Taxpayer.Address with 85% confidence. It even shows the exact file and line.
>
> For the fix, it suggests adding a null-safe access pattern with an optional fallback address, rates the risk as LOW, and provides verification test cases in C# that we can copy directly into our test project.
>
> This turns a potentially hours-long debugging session into minutes."

---

## 10. Demo Scenario 8: SDLC Tools - Test Generator

### Objective
Demonstrate automated test case generation for components.

### Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select "Test Generator" tab | Test generation interface appears |
| 2 | Enter component path (e.g., `CoreTax.Application/Handlers/SubmitInvoiceHandler.cs`) | Path entered |
| 3 | Select test type: "Unit Tests" | Unit test mode selected |
| 4 | Click "Generate Tests" | AI generates test code |
| 5 | Observe output | C# xUnit test class with Arrange-Act-Assert pattern, mocked dependencies |
| 6 | Select test type: "Edge Cases" | Edge case mode selected |
| 7 | Click "Generate Tests" | AI generates edge case scenarios |
| 8 | Observe output | Lists edge cases with name, description, input scenario, expected behavior |

### Narration Script

> "The Test Generator creates test skeletons for any component. Let me target the SubmitInvoiceHandler.
>
> For Unit Tests, it generates an xUnit test class with proper mocking of dependencies -- the repository, event publisher, and logger. Each test follows Arrange-Act-Assert pattern covering the happy path, validation failures, and exception handling.
>
> For Edge Cases, it identifies scenarios we might miss -- like submitting an invoice with zero line items, an invoice exceeding the maximum amount threshold, concurrent submission of the same invoice number, and submitting for a deactivated taxpayer.
>
> Each edge case includes the specific input scenario and expected behavior, making it easy to implement the actual test."

### Test Types

| Type | Output |
|------|--------|
| Unit Tests | Complete xUnit C# test class with mocked dependencies, Arrange-Act-Assert pattern |
| Integration Tests | Multi-component test scenarios with database/service setup |
| Edge Cases | Scenario name, description, input, expected behavior |

---

## 11. Demo Scenario 9: SDLC Tools - Architecture Validator

### Objective
Show automated validation of architecture rules against the crawled solution.

### Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select "Architecture Validator" tab | Validation interface appears |
| 2 | Confirm rules file path (default: `architecture_rules/coretax_rules.yaml`) | Path shown |
| 3 | Click "Validate Architecture" | Validation runs against last crawl report |
| 4 | Observe Metrics | Shows: Total rules checked, Passed, Failed, Warnings |
| 5 | Observe Violations list | Each violation shows: rule name, severity icon, file path, description, suggested fix |

### Narration Script

> "The Architecture Validator enforces our design rules automatically. It validates the crawled solution against a YAML rule set.
>
> The results show how many rules passed, failed, and generated warnings. For each violation, we see the severity -- error for critical issues, warning for best-practice deviations, and info for recommendations.
>
> For example, if a Presentation layer project directly references Infrastructure -- that's an architecture violation. The validator catches it and suggests the proper dependency path through Application layer.
>
> This ensures our Clean Architecture principles are maintained as the codebase grows."

### Severity Levels

| Icon | Severity | Meaning |
|------|----------|---------|
| !!! | Error | Critical architecture violation that must be fixed |
| ! | Warning | Best practice deviation that should be addressed |
| i | Info | Recommendation for improvement |

---

## 12. Demo Scenario 10: End-to-End Workflow

### Objective
Demonstrate the complete workflow from crawl to AI-powered analysis.

### Steps

| Step | Action | Time |
|------|--------|------|
| 1 | Initialize services (LLM + Knowledge Store) | ~5 sec |
| 2 | Crawl CoreTaxSample solution | ~10 sec |
| 3 | Review crawl results across all tabs | ~2 min |
| 4 | Download MD and PDF reports | ~5 sec |
| 5 | Ingest crawl report to Knowledge Store | ~10 sec |
| 6 | Ask RAG Chat: "Explain the CQRS pattern in this solution" | ~15 sec |
| 7 | Ask RAG Chat: "Trace the taxpayer registration flow" | ~15 sec |
| 8 | Use Flow Explorer to trace an endpoint | ~15 sec |
| 9 | Use Bug Resolution for a sample bug | ~15 sec |
| 10 | Generate tests for a handler | ~15 sec |
| **Total** | **Complete demo** | **~5 min** |

### Narration Script (Closing)

> "In just five minutes, we've demonstrated the full power of Lumen.AI:
>
> First, we crawled an 8-project .NET solution -- pulled in from a local path, but it could just as easily have been a ZIP upload or a GitHub URL -- and instantly discovered 19 endpoints, 6 consumers, 8 schedulers, 7 integrations, 5 data models, and the Angular front-end that calls them, with a layered dependency graph and per-domain sequence diagrams.
>
> Second, we generated complete technical documentation in both Markdown and PDF -- including business domains, cross-domain contracts, configurations, DI registrations, code symbols, sequence flows, and the full UI → API wiring -- ready for review or distribution.
>
> Third, we ingested everything into a RAG knowledge store and asked natural language questions about our architecture, flows, and impact of changes.
>
> Fourth, we used SDLC tools to analyze bugs, generate tests, and validate architecture.
>
> Lumen.AI transforms how teams understand, document, and maintain large polyglot codebases. It's not just a tool -- it's a knowledge engine that grows with your codebase."

---

## 13. Feature Summary Matrix

| Feature | Page | Description | Key Benefit |
|---------|------|-------------|-------------|
| Multi-Source Input | Solution Crawler | Crawl from local path, ZIP upload, or GitHub URL | Run reviews without disk-mount gymnastics |
| Solution Crawler | Solution Crawler | Auto-discover .NET solution architecture | Eliminate manual architecture documentation |
| Project Analysis | Solution Crawler > Projects | Detect projects, layers, frameworks, dependencies | Understand solution structure instantly |
| Endpoint Discovery | Solution Crawler > Endpoints | Find all REST API endpoints with auth info | Complete API inventory without manual listing |
| Consumer Discovery | Solution Crawler > Consumers | Detect MassTransit/RabbitMQ consumers & sagas | Map async message processing flows |
| Scheduler Discovery | Solution Crawler > Schedulers | Find Hangfire jobs, background services | Inventory all automated processes |
| Integration Detection | Solution Crawler > Integrations | Discover Redis, RabbitMQ, Consul, S3, HTTP, gRPC | Map external dependencies |
| Data Model Discovery | Solution Crawler > Data Models | Extract EF Core entities from DbContext | Understand data architecture |
| Angular Front-End Discovery | Solution Crawler | Auto-detect angular.json, extract components/modules/routes/API calls | Full-stack coverage in one crawl |
| UI → API Wiring | Generated Doc | Mermaid diagram connecting Angular components to back-end Controllers | See exactly which page hits which endpoint |
| Deep Code Analysis | Generated Doc | Extract DDD aggregates, domain events, value objects, repositories, controllers | Understand domain structure without reading every file |
| Configuration Extraction | Generated Doc | Pull every key from `appsettings.*.json`, `launchSettings.json`, `*.config` | Audit env-specific settings and secrets surface |
| DI Registration Discovery | Generated Doc | Catalogue every `Add*` registration with file:line | Trace any interface back to its concrete implementation |
| Business Domain Clustering | Generated Doc | Group projects + namespaces into bounded contexts | Discover the de-facto domain map |
| Cross-Domain Contracts | Generated Doc | Join named HTTP clients with config URLs | Surface every runtime cross-service dependency |
| Sequence Flow Diagrams | Generated Doc | Per-domain Mermaid sequenceDiagram of Client → Controllers → services → Bus → Consumers | Understand runtime interactions at a glance |
| Dependency Graph | Generated Doc | Layered Mermaid graph of references with contract overlay | See architecture at a glance |
| MD Report Generation | Solution Crawler | Auto-generate Markdown documentation | Instant technical docs |
| PDF Report Generation | Solution Crawler | Auto-generate PDF documentation (unicode-safe) | Shareable formatted reports |
| Knowledge Ingestion | Knowledge Store | Index crawl data into vector store | Enable AI-powered queries |
| Document Ingestion | Knowledge Store | Import markdown files and directories | Enrich knowledge base |
| RAG Chat - Explain | RAG Chat | AI explains code with architecture context | Deep code understanding |
| RAG Chat - Find | RAG Chat | Smart code search across solution | Find anything quickly |
| RAG Chat - Trace | RAG Chat | Trace business flows end-to-end | Understand complex flows |
| RAG Chat - Impact | RAG Chat | Change impact analysis | Safe refactoring |
| RAG Chat - Test | RAG Chat | AI suggests test cases | Better test coverage |
| Conversation History | RAG Chat | Persistent chat with browse/reload | Build on previous queries |
| Flow Tracing | Flow Explorer | Visual sequence diagrams of flows | See the big picture |
| Component Explainer | Flow Explorer | Deep-dive into any class/method | Onboard faster |
| Validation Extractor | Flow Explorer | Extract validation rules | Audit business rules |
| Bug Resolution | SDLC Tools | AI-powered bug analysis & fix suggestions | Debug faster |
| Test Generator | SDLC Tools | Generate unit/integration/edge test cases | Accelerate QA |
| Architecture Validator | SDLC Tools | Validate rules against crawl report | Enforce design standards |

---

## Appendix A: Sample Questions for RAG Chat

### Explain Mode
- "How does the CQRS pattern work in this solution?"
- "Explain the tax invoice lifecycle"
- "What is the role of CoreTax.Shared project?"
- "How does authentication work across controllers?"

### Find Mode
- "Where are the Hangfire job definitions?"
- "Find all classes that use IDistributedCache"
- "Where is the Consul service registration configured?"
- "Find the S3 document storage implementation"

### Trace Mode
- "Trace the taxpayer registration flow from API to database"
- "Trace what happens when a tax payment is processed"
- "Trace the audit scheduling flow"
- "Trace the invoice approval saga"

### Impact Mode
- "What would be affected if I change the TaxInvoice entity?"
- "Impact of modifying the payment gateway client"
- "What breaks if I remove the Redis caching service?"
- "Impact of changing the NPWP validation rules"

### Test Mode
- "Suggest tests for ProcessPaymentCommandHandler"
- "What edge cases should I test for tax return filing?"
- "Generate integration tests for the InvoiceController"
- "What should I test in the AuditScheduledConsumer?"

---

## Appendix B: CoreTaxSample Architecture

```
CoreTaxSample.sln
|
+-- CoreTax.Domain            (Entities, Value Objects, Enums)
|   +-- Taxpayer, TaxInvoice, TaxReturn, TaxPayment, TaxAudit
|   +-- Npwp (NPWP validation), Money (IDR currency)
|
+-- CoreTax.Contracts         (Commands & Events)
|   +-- RegisterTaxpayerCommand, SubmitInvoiceCommand, ...
|   +-- TaxpayerRegisteredEvent, InvoiceSubmittedEvent, ...
|
+-- CoreTax.Application       (Handlers, Queries, Validators, DTOs)
|   +-- 5 Command Handlers (MediatR IRequest pattern)
|   +-- 3 Query Handlers
|   +-- 2 FluentValidation Validators
|   +-- 3 DTO classes
|
+-- CoreTax.Infrastructure    (Persistence, Cache, Integrations)
|   +-- CoreTaxDbContext (EF Core, 5 DbSets)
|   +-- RedisCacheService (IDistributedCache)
|   +-- ConsulRegistrationService (Service Discovery)
|   +-- ElasticsearchLoggingConfig (ELK)
|   +-- TaxPaymentGatewayClient (HTTP)
|   +-- DocumentStorageService (AWS S3)
|
+-- CoreTax.Presentation      (API Controllers)
|   +-- TaxRegistrationController (3 endpoints)
|   +-- InvoiceController (4 endpoints)
|   +-- TaxReturnController (3 endpoints)
|   +-- PaymentController (3 endpoints)
|   +-- AuditController (4 endpoints)
|   +-- ReportController (2 endpoints, public)
|
+-- CoreTax.Worker            (Background Processing)
|   +-- 5 MassTransit Consumers
|   +-- 1 InvoiceApprovalSaga (State Machine)
|   +-- HangfireJobScheduler (3 recurring + enqueue + schedule)
|   +-- 2 Background Services
|
+-- CoreTax.Shared            (Cross-Cutting Concerns)
|   +-- JWT Token Service
|   +-- Authorization Handler
|   +-- Serilog + Elasticsearch Config
|
+-- CoreTax.Angular           (Frontend SPA)
    +-- 5 Feature Modules (registration, invoice, filing, payment, dashboard)
    +-- Each: Component + Module/Routes + Service
```

---

*Document generated for Lumen.AI Demo v1.1*
*Prepared for DJP CoreTax Development Team*

### Changelog (v1.1)

- Rebranded from **Neo-TDG** to **Lumen.AI**; subtitle no longer pinned to "for CoreTax"
- Default port moved from 8502 → 8503
- Top navigation reordered: Solution Crawler → Knowledge Store → RAG Chat → Flow Explorer → SDLC Tools
- **Multi-source crawler input**: Local Path, Upload Solution (ZIP), GitHub Repository
- **Deep code & configuration analysis** opt-in (default on this branch via `crawler.deep_analysis.enabled: true`): configurations, DI registrations, code symbols, business domains, cross-domain contracts
- **Sequence Flows** section in generated docs — per-business-domain Mermaid `sequenceDiagram`
- **Dependency Graph** section rewritten — layered subgraphs, contract overlay, edge table
- **Angular front-end discovery** — auto-detect `angular.json` under the solution directory (with optional override field); generates a per-module component table and a `UI → API Wiring` Mermaid diagram in the doc
- PDF generator now sanitizes em-dashes, arrows, and other unicode characters so the download button never disappears silently
