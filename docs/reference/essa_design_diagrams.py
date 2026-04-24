"""Generate diagrams for the lumen.ai KT-Pro design document.
Outputs (PNG) to /sessions/confident-admiring-bohr/mnt/outputs/analysis/design/
"""
from PIL import Image, ImageDraw, ImageFont
import os, math

OUT = '/sessions/confident-admiring-bohr/mnt/outputs/analysis/design'
os.makedirs(OUT, exist_ok=True)

def fnt(sz, bold=False):
    c = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(c, sz) if os.path.exists(c) else ImageFont.load_default()

F_TITLE = fnt(26, bold=True)
F_H     = fnt(18, bold=True)
F_HS    = fnt(16, bold=True)
F_B     = fnt(15, bold=True)
F_T     = fnt(14)
F_S     = fnt(13)
F_XS    = fnt(12)

def rounded(d, x, y, w, h, fill, outline=None, r=12):
    outline = outline or fill
    d.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=outline, width=2)

def centered(d, x, y, w, h, lines, color="white", fonts=None):
    fonts = fonts or [F_H] + [F_S] * (len(lines) - 1)
    if len(fonts) < len(lines):
        fonts = fonts + [F_S] * (len(lines) - len(fonts))
    tmp = ImageDraw.Draw(Image.new("RGB", (1,1)))
    lh = [tmp.textbbox((0,0), ln, font=fonts[i])[3] + 4 for i, ln in enumerate(lines)]
    total = sum(lh)
    yy = y + (h - total) / 2
    for i, ln in enumerate(lines):
        tw = d.textlength(ln, font=fonts[i])
        d.text((x + (w - tw) / 2, yy), ln, fill=color, font=fonts[i])
        yy += lh[i]

def arrow(d, x1, y1, x2, y2, color="#333", width=3, head=12, dashed=False):
    if dashed:
        dx, dy = x2-x1, y2-y1
        L = math.hypot(dx, dy)
        n = max(2, int(L / 12))
        for s in range(n):
            t0, t1 = s/n, (s+0.5)/n
            d.line([(x1+dx*t0, y1+dy*t0), (x1+dx*t1, y1+dy*t1)], fill=color, width=width)
    else:
        d.line([(x1, y1), (x2, y2)], fill=color, width=width)
    ang = math.atan2(y2-y1, x2-x1)
    ax = x2 - head*math.cos(ang-math.pi/7); ay = y2 - head*math.sin(ang-math.pi/7)
    bx = x2 - head*math.cos(ang+math.pi/7); by = y2 - head*math.sin(ang+math.pi/7)
    d.polygon([(x2, y2), (ax, ay), (bx, by)], fill=color)

def title(d, W, text):
    tw = d.textlength(text, font=F_TITLE)
    d.text(((W - tw)/2, 18), text, fill="#1F4E79", font=F_TITLE)

# =========================================================
# 1) CURRENT vs TARGET
# =========================================================
W, H = 2000, 1100
img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
title(d, W, "Figure 4.1 — lumen.ai: Current vs Target Architecture")

def stack(x, y, color_title, items, heading):
    # heading bar
    rounded(d, x, y, 820, 60, color_title)
    centered(d, x, y, 820, 60, [heading], fonts=[F_H])
    yy = y + 80
    for (name, sub, color) in items:
        rounded(d, x, yy, 820, 80, color)
        centered(d, x, yy, 820, 80, [name, sub], fonts=[F_B, F_S])
        yy += 90
    return yy

# LEFT: Current
left_items = [
    ("1. File crawler",          "Walks .sln, .csproj, .cs files only",              "#7C8999"),
    ("2. LLM prose generator",   "One-shot prompt → plain Word doc",                 "#7C8999"),
    ("3. Minimal template",      "Fixed sections, no persona targeting",             "#7C8999"),
    ("4. Single output",          "One generic document per solution",               "#7C8999"),
    ("— Gaps —",                 "No diagrams, no recs, no RAG, no chatbot",          "#A93226"),
]
stack(80, 90, "#7C8999", left_items, "CURRENT — lumen.ai today")

# RIGHT: Target
right_items = [
    ("1. Multi-source ingester", ".sln/.csproj + configs/IaC/Docker/SQL/tests",       "#0F6FC6"),
    ("2. Structured analyser",   "Roslyn AST + dep graph + security scan",            "#2E8B57"),
    ("3. Persona-aware outline", "Architect / Dev / QA / L1 / L2 / L3",                "#16A085"),
    ("4. Evidence-grounded draft","Claims cite file:line, auto citations",             "#C05621"),
    ("5. Diagram + recs engine", "Mermaid/PlantUML + best-practice checks",           "#6A5ACD"),
    ("6. QA & validation",       "OOXML validate, self-critique, reviewer gate",      "#1F4E79"),
    ("7. RAG ingestion + Chat",  "Vector index + chatbot over docs & code",           "#B22222"),
]
stack(1100, 90, "#0F6FC6", right_items, "TARGET — lumen.ai + KT-Pro")

# Big arrow between
arrow(d, 920, 530, 1080, 530, color="#333", width=5, head=18)
d.text((905, 480), "upgrade", fill="#1F4E79", font=F_H)

# Bottom: quality wins
rounded(d, 80, 950, W-160, 120, "#F7F9FC", outline="#B5C7DD", r=14)
centered(d, 80, 950, W-160, 40, ["Quality wins"], color="#1F4E79", fonts=[F_H])
wins = [
    "Higher factual accuracy (code-grounded)",
    "Right doc for the right role (6 personas)",
    "Actionable recommendations",
    "Knowledge you can talk to (RAG chatbot)",
]
cw = (W - 160) / len(wins)
for i, w in enumerate(wins):
    cx = 80 + i*cw
    d.text((cx + 30, 1010), "✓ " + w, fill="#1F4E79", font=F_B)

img.save(f"{OUT}/01_current_vs_target.png")
print("01 ok")

# =========================================================
# 2) GENERATION PIPELINE (persona-aware, end to end)
# =========================================================
W, H = 2200, 1200
img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
title(d, W, "Figure 5.1 — Persona-Aware Generation Pipeline (KT-Pro)")

# lane labels (vertical swim-lanes)
lanes = [
    ("INGEST",        80,  "#1F4E79"),
    ("PARSE",         380, "#0F6FC6"),
    ("UNDERSTAND",    680, "#2E8B57"),
    ("PLAN",          980, "#16A085"),
    ("DRAFT",         1280,"#C05621"),
    ("DIAGRAMS+RECS", 1580,"#6A5ACD"),
    ("VALIDATE+EXPORT",1880,"#B22222"),
]
for name, x, color in lanes:
    rounded(d, x, 80, 240, 52, color)
    centered(d, x, 80, 240, 52, [name], fonts=[F_H])

# per-stage items
def card(x, y, title_txt, body, color, w=240, h=88):
    rounded(d, x, y, w, h, color)
    centered(d, x, y, w, h, [title_txt, body], color="white", fonts=[F_B, F_XS])

# stage content
card(80,  170, "Git / folder loader",   "sln, csproj, cs, configs, SQL, IaC", "#1F4E79")
card(80,  280, "Secret scrubber",       "Remove tokens, hostnames",            "#1F4E79")
card(80,  390, "File classifier",       "entry point / controller / DI / ...",  "#1F4E79")

card(380, 170, "Roslyn AST",            "types, symbols, refs, xmldoc",         "#0F6FC6")
card(380, 280, "Dep graph",             "NuGet + project refs",                 "#0F6FC6")
card(380, 390, "Security scan",         "Semgrep / OSS-scanner",                 "#0F6FC6")
card(380, 500, "Test coverage map",     "xUnit / NUnit presence",                "#0F6FC6")

card(680, 170, "Responsibility map",    "file → role (Controller/Repo/...)",    "#2E8B57")
card(680, 280, "Data-flow inference",   "per endpoint / job",                    "#2E8B57")
card(680, 390, "Architecture style",    "layered / hexagonal / MVC",             "#2E8B57")
card(680, 500, "Evidence store",        "claim ⇢ file:line JSON",                "#2E8B57")

card(980, 170, "Persona selector",      "Arch / Dev / QA / L1 / L2 / L3",        "#16A085")
card(980, 280, "Outline template",      "per-persona section list",              "#16A085")
card(980, 390, "Audience tuning",       "depth, tone, examples",                 "#16A085")

card(1280,170, "Section drafter",       "LLM + evidence context",                "#C05621")
card(1280,280, "Table/FAQ extractor",   "structured JSON → tables",              "#C05621")
card(1280,390, "Glossary normaliser",   "consistent terminology",                "#C05621")
card(1280,500, "Tone & bias check",     "plain English, neutral",                "#C05621")

card(1580,170, "Mermaid/PlantUML gen",  "sequence, component, context",          "#6A5ACD")
card(1580,280, "Image renderer",        "mmdc / PlantUML / D2",                  "#6A5ACD")
card(1580,390, "Recommendations",       "patterns, perf, security, ops",         "#6A5ACD")
card(1580,500, "Risk register",         "HIGH/MED/LOW with rationale",           "#6A5ACD")

card(1880,170, "DOCX compose",          "docx-js or python-docx",                "#B22222")
card(1880,280, "OOXML validate",        "validate.py",                           "#B22222")
card(1880,390, "Self-critique pass",    "LLM reviewer gate",                     "#B22222")
card(1880,500, "PDF export",            "LibreOffice headless",                  "#B22222")
card(1880,610, "Publish",               "S3 + notify + index RAG",               "#B22222")

# lane-to-lane arrows (at top)
for i in range(len(lanes) - 1):
    x1 = lanes[i][1] + 240
    x2 = lanes[i+1][1]
    arrow(d, x1+2, 106, x2-2, 106, color="#333", width=3)

# Feedback loops (under the stages)
d.text((680, 780), "Feedback loops", fill="#1F4E79", font=F_H)
arrow(d, 2000, 820, 1200, 820, color="#666", dashed=True, width=2)
d.text((1230, 790), "Self-critique reveals missing evidence → back to UNDERSTAND", fill="#666", font=F_T)
arrow(d, 2000, 880, 800, 880, color="#666", dashed=True, width=2)
d.text((830, 850), "QA failure → Parse again or re-draft section", fill="#666", font=F_T)

# Output bar
rounded(d, 80, 980, W-160, 120, "#EAF3FB", outline="#B5C7DD", r=14)
centered(d, 80, 980, W-160, 40, ["Per-run outputs"], color="#1F4E79", fonts=[F_H])
out_items = ["KT.docx per persona", "KT.pdf per persona", "figures/*.png",
             "evidence.json (claim→file:line)", "model.json (repo graph)", "embeddings → RAG"]
cw = (W - 160) / len(out_items)
for i, o in enumerate(out_items):
    cx = 80 + i*cw + 20
    d.text((cx, 1040), "• " + o, fill="#1F4E79", font=F_B)

img.save(f"{OUT}/02_pipeline.png")
print("02 ok")

# =========================================================
# 3) PERSONA x DOC MATRIX
# =========================================================
W, H = 2200, 1300
img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
title(d, W, "Figure 6.1 — Persona × Document Variant Matrix")

personas = [
    ("Architect",     "#1F4E79"),
    ("Developer",     "#0F6FC6"),
    ("Tester / QA",   "#2E8B57"),
    ("Support L1",    "#16A085"),
    ("Support L2",    "#C05621"),
    ("Support L3",    "#B22222"),
]
# document variants
docs = [
    "Solution Architecture Blueprint",
    "ADR Log (decisions)",
    "System Context & Component Model",
    "Tech Stack & NFR Rationale",
    "Developer Onboarding Guide",
    "Code Walkthrough (module-by-module)",
    "API Reference & Contract",
    "Extension Recipes (how to add …)",
    "Test Plan & Test Scenarios",
    "Data & Fixtures Setup",
    "Regression Checklist",
    "L1 Quick Reference Card",
    "L2 Runbook & Triage Playbook",
    "L3 Deep-Dive & Hotfix SOP",
    "Monitoring / Alerts Guide",
    "Security & Compliance Brief",
]

# mapping (X = primary, o = useful)
#                   Arch Dev QA  L1  L2  L3
mapping = {
    "Solution Architecture Blueprint":    [2,1,1,0,0,1],
    "ADR Log (decisions)":                 [2,1,0,0,0,1],
    "System Context & Component Model":    [2,2,1,0,1,1],
    "Tech Stack & NFR Rationale":          [2,1,1,0,0,1],
    "Developer Onboarding Guide":          [1,2,1,0,0,2],
    "Code Walkthrough (module-by-module)": [1,2,1,0,0,2],
    "API Reference & Contract":            [1,2,2,0,1,2],
    "Extension Recipes (how to add …)":    [1,2,1,0,0,2],
    "Test Plan & Test Scenarios":          [1,1,2,0,0,1],
    "Data & Fixtures Setup":               [0,1,2,0,1,1],
    "Regression Checklist":                [0,1,2,0,1,1],
    "L1 Quick Reference Card":             [0,0,0,2,1,0],
    "L2 Runbook & Triage Playbook":        [0,1,0,1,2,1],
    "L3 Deep-Dive & Hotfix SOP":           [1,2,0,0,1,2],
    "Monitoring / Alerts Guide":           [1,1,1,1,2,1],
    "Security & Compliance Brief":         [2,1,1,0,1,1],
}

# layout grid
left_w = 560
cell_w = (W - 160 - left_w) / len(personas)
row_h = 56
top = 110

# header row
d.rectangle([80, top, 80+left_w, top+50], fill="#1F4E79")
d.text((92, top+14), "Document variant", fill="white", font=F_H)
for i, (p, c) in enumerate(personas):
    x = 80 + left_w + i*cell_w
    rounded(d, x+4, top, cell_w-8, 50, c)
    tw = d.textlength(p, font=F_H)
    d.text((x + (cell_w - tw)/2, top + 14), p, fill="white", font=F_H)

# rows
for ri, doc in enumerate(docs):
    y = top + 60 + ri*row_h
    # row header
    fill = "#F7F9FC" if ri % 2 == 0 else "white"
    d.rectangle([80, y, 80+left_w, y+row_h-4], fill=fill, outline="#D9D9D9")
    d.text((96, y + 18), doc, fill="#333", font=F_B)
    for i, (p, color) in enumerate(personas):
        x = 80 + left_w + i*cell_w
        d.rectangle([x+4, y, x+cell_w-4, y+row_h-4], fill=fill, outline="#D9D9D9")
        v = mapping[doc][i]
        cx = x + cell_w/2
        cy = y + row_h/2
        if v == 2:
            # primary — filled rounded badge sized to the label
            label = "PRIMARY"
            tw = d.textlength(label, font=F_XS)
            bw = tw + 22; bh = 24
            d.rounded_rectangle([cx-bw/2, cy-bh/2, cx+bw/2, cy+bh/2], radius=6, fill=color)
            d.text((cx - tw/2, cy - 8), label, fill="white", font=F_XS)
        elif v == 1:
            label = "useful"
            tw = d.textlength(label, font=F_XS)
            bw = tw + 18; bh = 22
            d.rounded_rectangle([cx-bw/2, cy-bh/2, cx+bw/2, cy+bh/2], radius=5, outline=color, width=2)
            d.text((cx - tw/2, cy - 8), label, fill=color, font=F_XS)
        else:
            d.text((cx - 4, cy - 8), "—", fill="#AAA", font=F_T)

# legend
ly = top + 60 + len(docs)*row_h + 20
d.rounded_rectangle([80, ly, 240, ly+28], radius=5, fill="#0F6FC6")
d.text((90, ly+4), "PRIMARY", fill="white", font=F_B)
d.text((250, ly+4), "= main audience, receives the full-depth variant", fill="#333", font=F_T)

d.rounded_rectangle([800, ly, 940, ly+28], radius=5, outline="#0F6FC6", width=2)
d.text((820, ly+4), "useful", fill="#0F6FC6", font=F_B)
d.text((950, ly+4), "= secondary audience, receives a lighter summary", fill="#333", font=F_T)

img.save(f"{OUT}/03_persona_matrix.png")
print("03 ok")

# =========================================================
# 4) RAG INGESTION + CHATBOT
# =========================================================
W, H = 2200, 1100
img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
title(d, W, "Figure 12.1 — RAG Ingestion & Chatbot Flow")

# top lane: ingestion pipeline
def card2(x, y, w, h, t, sub, color):
    rounded(d, x, y, w, h, color)
    centered(d, x, y, w, h, [t, sub], color="white", fonts=[F_B, F_S])

# Ingestion track
y0 = 110
d.text((80, 80), "A. Ingestion (triggered per KT-Pro run)", fill="#1F4E79", font=F_H)
chain = [
    ("Generated KT.docx",   "one per persona",           "#1F4E79"),
    ("Source code chunks",  "code + xmldoc + configs",    "#0F6FC6"),
    ("Evidence JSON",       "claim → file:line",          "#2E8B57"),
    ("Chunker",             "semantic + size-aware",      "#16A085"),
    ("Embedder",            "Voyage / text-embedding-3",  "#C05621"),
    ("Vector DB",           "pgvector / Qdrant",          "#6A5ACD"),
    ("Keyword index",       "BM25 (Postgres tsvector)",   "#1F4E79"),
]
cw, ch = 260, 110; gap = 20
x = 80
for i, (t, s, c) in enumerate(chain):
    card2(x, y0, cw, ch, t, s, c)
    if i < len(chain)-1:
        arrow(d, x+cw+4, y0+ch/2, x+cw+gap-4, y0+ch/2)
    x += cw + gap

# Retrieval + Chat track (below)
y1 = 360
d.text((80, 330), "B. Retrieval & Chat", fill="#1F4E79", font=F_H)
# User / UI
card2(80,  y1, 220, 110, "Chat UI",          "Web + Slack/Teams",             "#16A085")
card2(340, y1, 220, 110, "Auth & persona",   "tenant, role, permissions",     "#2E8B57")
card2(600, y1, 220, 110, "Query router",     "classify intent + persona",      "#0F6FC6")
card2(860, y1, 220, 110, "Hybrid retrieve",  "BM25 + vector + metadata filter","#6A5ACD")
card2(1120,y1, 220, 110, "Reranker",         "Cohere / cross-encoder",          "#C05621")
card2(1380,y1, 220, 110, "LLM answerer",     "Claude w/ cited context",         "#B22222")
card2(1640,y1, 220, 110, "Answer + citations","file:line + doc section",        "#1F4E79")
card2(1900,y1, 220, 110, "Feedback loop",    "thumbs • reruns • notes",         "#2E8B57")

# arrows
xs = [300,560,820,1080,1340,1600,1860]
for x in xs:
    arrow(d, x+4, y1+55, x+20-4+10, y1+55)

# Link ingestion → retrieval
arrow(d, 80+6*(cw+gap)+cw/2, y0+ch+4, 980, y1-4, color="#6A5ACD", width=3)
d.text((1000, (y0+ch+y1)/2 - 10), "index is queried at retrieval time", fill="#6A5ACD", font=F_T)

# Persona filter + citations
rounded(d, 80, 640, W-160, 240, "#F7F9FC", outline="#B5C7DD", r=14)
centered(d, 80, 640, W-160, 40, ["Retrieval guardrails"], color="#1F4E79", fonts=[F_H])
items = [
    ("Persona-aware filter",   "Architect asks → prefer blueprint/ADR; L2 asks → prefer runbook"),
    ("Freshness filter",       "Prefer chunks from the latest analysis run; demote stale docs"),
    ("Citation enforcement",   "Reject answers without at least one file:line OR doc-section citation"),
    ("Fallback path",          "If vector recall < threshold, escalate to full-file read of top candidate"),
    ("Audit log",              "Every Q/A stored with retrieved chunk IDs for traceability"),
]
rx, ry = 120, 710
col_w = (W - 240) / 2
for i, (t, b) in enumerate(items):
    x = rx + (i % 2) * col_w
    y = ry + (i // 2) * 48
    d.text((x, y), "• " + t + " — ", fill="#1F4E79", font=F_B)
    d.text((x + d.textlength("• " + t + " — ", font=F_B), y), b, fill="#333", font=F_T)

# bottom row: outputs for chat
rounded(d, 80, 920, W-160, 130, "#EAF3FB", outline="#B5C7DD", r=14)
centered(d, 80, 920, W-160, 40, ["Chat answer contract"], color="#1F4E79", fonts=[F_H])
blurbs = [
    "Direct answer (plain English, persona-tuned)",
    "Evidence: [file.cs:L42] • [KT §4.1]",
    "Related next actions (open ticket, regenerate doc, view diagram)",
]
cw2 = (W - 160) / len(blurbs)
for i, b in enumerate(blurbs):
    cx = 80 + i*cw2 + 20
    d.text((cx, 990), "▣ " + b, fill="#1F4E79", font=F_B)

img.save(f"{OUT}/04_rag_chat.png")
print("04 ok")

# =========================================================
# 5) LUMEN INTEGRATION
# =========================================================
W, H = 2200, 1240
img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
title(d, W, "Figure 14.1 — KT-Pro inside lumen.ai (integration points)")

# lumen.ai outer container
rounded(d, 60, 80, W-120, 1120, "#F7F9FC", outline="#0F6FC6", r=16)
d.text((90, 95), "lumen.ai platform", fill="#0F6FC6", font=F_TITLE)

# Existing modules (gray)
def module(x, y, w, h, name, sub, color):
    rounded(d, x, y, w, h, color)
    centered(d, x, y, w, h, [name, sub], color="white", fonts=[F_B, F_S])

existing_y = 180
d.text((100, existing_y - 40), "Existing lumen.ai services (reused)", fill="#555", font=F_H)
module(100, existing_y, 340, 90, "Auth / Tenant",    "SSO, RBAC, workspaces",   "#7C8999")
module(460, existing_y, 340, 90, "Repo loader",      "Git clone / SSH keys",     "#7C8999")
module(820, existing_y, 340, 90, "Job orchestrator", "BullMQ / Temporal",        "#7C8999")
module(1180, existing_y, 340, 90, "Artifact store", "S3 / blob + metadata",     "#7C8999")
module(1540, existing_y, 340, 90, "Web UI + API",   "React front-end",          "#7C8999")

# NEW modules
new_y = 370
d.text((100, new_y - 40), "New KT-Pro modules", fill="#1F4E79", font=F_H)
module(100,  new_y, 340, 110, "Analyser service",      "Roslyn + Semgrep + xmldoc",  "#0F6FC6")
module(460,  new_y, 340, 110, "Understanding engine",  "Claude Agent SDK loop",      "#2E8B57")
module(820,  new_y, 340, 110, "Persona composer",      "6 personas, 16 variants",    "#16A085")
module(1180, new_y, 340, 110, "Diagram renderer",      "Mermaid / PlantUML / D2",    "#6A5ACD")
module(1540, new_y, 340, 110, "Doc writer + validator","docx-js, OOXML validator",   "#C05621")

# Cross-cutting: RAG + Chat
rag_y = 580
d.text((100, rag_y - 40), "Knowledge & Chat", fill="#1F4E79", font=F_H)
module(100,  rag_y, 540, 120, "Embedding + Vector DB", "pgvector / Qdrant + BM25",   "#B22222")
module(660,  rag_y, 540, 120, "Retrieval + Reranker",  "hybrid + persona filter",    "#6A5ACD")
module(1220, rag_y, 660, 120, "Chat gateway",          "Web + Slack + Teams + MCP",  "#1F4E79")

# External integrations
ext_y = 800
d.text((100, ext_y - 40), "External integrations / Connectors (MCP where possible)", fill="#1F4E79", font=F_H)
module(100,  ext_y, 300, 90, "GitHub / GitLab",  "repos + PR context", "#555555")
module(420,  ext_y, 300, 90, "Jira / Asana",     "link to tickets",     "#555555")
module(740,  ext_y, 300, 90, "Confluence / Notion","publish KT",        "#555555")
module(1060, ext_y, 300, 90, "Slack / Teams",    "chatbot surface",     "#555555")
module(1380, ext_y, 300, 90, "CI (GitHub Actions)", "auto-KT on merge", "#555555")
module(1700, ext_y, 300, 90, "Observability",    "OTEL, Prom, Sentry",  "#555555")

# arrows top→new→rag
for x in [270, 630, 990, 1350, 1710]:
    arrow(d, x, existing_y + 90 + 2, x, new_y - 2, color="#333", width=3)
arrow(d, 270,  new_y + 110 + 2, 370,  rag_y - 2, color="#333", width=3)
arrow(d, 990,  new_y + 110 + 2, 990,  rag_y - 2, color="#333", width=3)
arrow(d, 1350, new_y + 110 + 2, 1550, rag_y - 2, color="#333", width=3)

# rag → chat
arrow(d, 640, rag_y + 60, 660, rag_y + 60)
arrow(d, 1200, rag_y + 60, 1220, rag_y + 60)

# External
for x in [250, 570, 890, 1210, 1530, 1850]:
    arrow(d, x, new_y + 110 + 10, x, ext_y - 2, color="#999", width=2, dashed=True)

# Bottom callouts — two-column vertical list (prevents overlap)
rounded(d, 100, 960, W-200, 200, "#EAF3FB", outline="#B5C7DD", r=14)
centered(d, 100, 960, W-200, 40, ["Key design principles"], color="#1F4E79", fonts=[F_H])
pr = [
    "Reuse lumen.ai's Auth, Jobs and Storage — don't rebuild",
    "Every generated claim is cited (file:line or doc §)",
    "Personas are first-class: they drive outline, depth and tone",
    "Artefacts are versioned and indexed automatically",
    "Chat answers quote and link back to the generated docs",
    "Analyser findings feed the Recommendations engine (not prose)",
]
col_w = (W - 240) / 2
for i, p in enumerate(pr):
    col = i % 2
    row = i // 2
    x = 120 + col * col_w
    y = 1010 + row * 44
    d.text((x, y), "• " + p, fill="#1F4E79", font=F_B)

img.save(f"{OUT}/05_lumen_integration.png")
print("05 ok")

# =========================================================
# 6) ROADMAP
# =========================================================
W, H = 2200, 820
img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
title(d, W, "Figure 19.1 — Rollout Roadmap (5 phases)")

phases = [
    ("Phase 0",  "Audit",        "2 wks",   "Baseline current lumen.ai output",   "#7C8999"),
    ("Phase 1",  "Grounding",    "4-6 wks", "Roslyn + evidence-grounded draft\nPersona 'Developer' only",       "#0F6FC6"),
    ("Phase 2",  "Expand",       "6-8 wks", "Add Architect, L2, L3 personas\nDiagrams + recs engine\nValidator", "#2E8B57"),
    ("Phase 3",  "RAG + Chat",   "6 wks",   "Ingestion, vector DB, chat UI",      "#6A5ACD"),
    ("Phase 4",  "Scale",        "ongoing", "Multi-language, CI plugin\nMCP connectors, enterprise tenants",    "#C05621"),
]
cw = (W - 160) / len(phases)
for i, (ph, name, d_, body, color) in enumerate(phases):
    x = 80 + i*cw
    rounded(d, x+10, 110, cw-20, 540, color)
    centered(d, x+10, 110, cw-20, 60, [ph], fonts=[F_H])
    centered(d, x+10, 180, cw-20, 50, [name], fonts=[F_HS])
    centered(d, x+10, 240, cw-20, 40, [d_], fonts=[F_S])
    # body
    yb = 300
    for ln in body.split("\n"):
        tw = d.textlength(ln, font=F_T)
        d.text((x + (cw - tw)/2, yb), ln, fill="white", font=F_T)
        yb += 28

# arrow across
arrow(d, 80, 680, W-80, 680, color="#1F4E79", width=5, head=20)
d.text((80, 700), "time  →", fill="#1F4E79", font=F_H)

# success metrics strip
rounded(d, 80, 730, W-160, 70, "#EAF3FB", outline="#B5C7DD", r=12)
metrics = ["% of claims with citations", "Doc review acceptance rate",
           "Time to produce KT (hours)", "Chat answer CSAT",
           "RAG retrieval precision@5"]
cw2 = (W - 160)/len(metrics)
for i, m in enumerate(metrics):
    d.text((90 + i*cw2, 752), "✓ " + m, fill="#1F4E79", font=F_B)

img.save(f"{OUT}/06_roadmap.png")
print("06 ok")

print("ALL DONE")
