"""Render the remaining three diagrams:
 - context_diagram.png   (§2 System Context)
 - module_diagram.png    (§3.1 Internal module dependencies)
 - topology_diagram.png  (§7.2 Runtime topology)
"""
from PIL import Image, ImageDraw, ImageFont
import os

def load_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()

F_TITLE = load_font(26, bold=True)
F_H     = load_font(20, bold=True)
F_B     = load_font(17, bold=True)
F_T     = load_font(16)
F_S     = load_font(14)
F_LBL   = load_font(15, bold=True)

OUTDIR = '/sessions/confident-admiring-bohr/mnt/outputs/analysis'

# ---------- shared helpers ----------
def draw_box(draw, x, y, w, h, fill, outline=None, radius=12):
    outline = outline or fill
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill, outline=outline, width=2)

def draw_label(draw, x, y, w, h, lines, color="white", fonts=None):
    fonts = fonts or [F_B]
    if len(fonts) < len(lines):
        fonts = fonts + [F_T] * (len(lines) - len(fonts))
    line_h = [ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), ln, font=fonts[i])[3] + 4 for i, ln in enumerate(lines)]
    total = sum(line_h)
    yy = y + (h - total) / 2
    for i, ln in enumerate(lines):
        tw = draw.textlength(ln, font=fonts[i])
        draw.text((x + (w - tw) / 2, yy), ln, fill=color, font=fonts[i])
        yy += line_h[i]

def arrow(draw, x1, y1, x2, y2, color="#333", width=3, dashed=False, head=12):
    if dashed:
        # manual dashed
        import math
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        steps = max(2, int(L / 12))
        for s in range(steps):
            t0 = s / steps
            t1 = (s + 0.5) / steps
            draw.line([(x1 + dx * t0, y1 + dy * t0), (x1 + dx * t1, y1 + dy * t1)], fill=color, width=width)
    else:
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    # arrowhead
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    ax1 = x2 - head * math.cos(ang - math.pi / 7)
    ay1 = y2 - head * math.sin(ang - math.pi / 7)
    ax2 = x2 - head * math.cos(ang + math.pi / 7)
    ay2 = y2 - head * math.sin(ang + math.pi / 7)
    draw.polygon([(x2, y2), (ax1, ay1), (ax2, ay2)], fill=color)

def edge_label(draw, x1, y1, x2, y2, text, color="#1F4E79", offset=12, font=F_LBL):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    tw = draw.textlength(text, font=font)
    # slight up-offset
    draw.rectangle([mx - tw / 2 - 6, my - offset - 14, mx + tw / 2 + 6, my - offset + 6], fill="white")
    draw.text((mx - tw / 2, my - offset - 12), text, fill=color, font=font)

# =========================================================
# 1) CONTEXT DIAGRAM (§2)
# =========================================================
W, H = 1800, 820
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)

title = "Figure 2.1 — ESSA System Context"
tw = d.textlength(title, font=F_TITLE)
d.text(((W - tw) / 2, 20), title, fill="#1F4E79", font=F_TITLE)

# Actor boxes
box_w, box_h = 340, 140
y_mid = 320
boxes = [
    ("Plant / OPC UA Server",      ["Plant / OPC UA Server", "PLCs • SCADA • Historian",  "opc.tcp:// port 4840 or 53530"],         100, y_mid, "#B22222"),
    ("ESSA WebApi",                ["ESSA WebApi",           "ASP.NET Web API 2 on IIS",   "Windows Server / .NET 4.8"],            (W - box_w) / 2, y_mid, "#0F6FC6"),
    ("BI / Dashboards / Integrations", ["BI / Dashboards",    "Power BI, Grafana,",         "Integration Services"],                 W - 100 - box_w, y_mid, "#2E8B57"),
]
positions = {}
for name, lines, x, y, color in boxes:
    draw_box(d, x, y, box_w, box_h, color)
    draw_label(d, x, y, box_w, box_h, lines, color="white", fonts=[F_H, F_T, F_S])
    positions[name] = (x, y, box_w, box_h)

# Arrows between them
def right_arrow_between(a, b, label):
    xa, ya, wa, ha = positions[a]
    xb, yb, wb, hb = positions[b]
    arrow(d, xa + wa + 10, ya + ha / 2, xb - 10, yb + hb / 2, color="#333", width=3)
    edge_label(d, xa + wa + 10, ya + ha / 2, xb - 10, yb + hb / 2, label)

right_arrow_between("Plant / OPC UA Server", "ESSA WebApi", "opc.tcp:// (binary)")
right_arrow_between("ESSA WebApi", "BI / Dashboards / Integrations", "HTTPS / JSON")

# WebService side-channel (below WebApi)
wsx = (W - box_w) / 2
wsy = y_mid + 240
draw_box(d, wsx, wsy, box_w, 110, "#6A5ACD")
draw_label(d, wsx, wsy, box_w, 110, ["ESSA WebService (SOAP)", "optional — currently Hello World only"], color="white", fonts=[F_H, F_S])
# dashed arrow up from WebService to WebApi
arrow(d, wsx + box_w / 2, wsy - 6, wsx + box_w / 2, y_mid + box_h + 6, color="#666", width=2, dashed=True)
edge_label(d, wsx + box_w / 2, wsy - 6, wsx + box_w / 2, y_mid + box_h + 6, "optional (not wired today)")

# legend: solid vs dashed (below the WebService box)
ly = 760
d.line([(100, ly), (160, ly)], fill="#333", width=3); arrow(d, 160, ly, 180, ly, color="#333")
d.text((200, ly - 10), "active data path", fill="#333", font=F_T)
x0 = 520
import math
for s in range(6):
    sx = x0 + s * 10
    d.line([(sx, ly), (sx + 5, ly)], fill="#666", width=2)
arrow(d, x0 + 60, ly, x0 + 80, ly, color="#666")
d.text((x0 + 100, ly - 10), "optional / not wired today", fill="#333", font=F_T)

img.save(f"{OUTDIR}/context_diagram.png")
print("wrote context_diagram.png", os.path.getsize(f"{OUTDIR}/context_diagram.png"), "bytes")

# =========================================================
# 2) MODULE DIAGRAM (§3.1)
# =========================================================
W, H = 1800, 900
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)

title = "Figure 3.1 — ESSA Internal Module Dependencies"
tw = d.textlength(title, font=F_TITLE)
d.text(((W - tw) / 2, 20), title, fill="#1F4E79", font=F_TITLE)

# Left column: three projects
proj_w, proj_h = 280, 100
proj_x = 100
col_ys = [160, 320, 480]
projects = [
    ("ConsoleApp1",           ["ConsoleApp1",           "Console Application",     "(support / diagnostics tool)"], "#2E8B57"),
    ("WebApi",                ["WebApi",                "ASP.NET MVC 5 + Web API 2","(deployable — IIS)"],           "#0F6FC6"),
    ("WebService",            ["WebService",            "ASMX (legacy SOAP)",      "(Hello World only — stub)"],    "#6A5ACD"),
]
proj_pos = {}
for (key, lines, color), y in zip(projects, col_ys):
    draw_box(d, proj_x, y, proj_w, proj_h, color)
    draw_label(d, proj_x, y, proj_w, proj_h, lines, color="white", fonts=[F_H, F_T, F_S])
    proj_pos[key] = (proj_x, y, proj_w, proj_h)

# Middle: Opc.Ua library
mid_x = 720
mid_y = 320
mid_w, mid_h = 300, 100
draw_box(d, mid_x, mid_y, mid_w, mid_h, "#C05621")
draw_label(d, mid_x, mid_y, mid_w, mid_h, ["Opc.Ua", "Class Library (.NET 4.8)", "core: ServerConnector, ClassRawData,", "Interfaces, TagCollection, AutoMapper"], color="white", fonts=[F_H, F_T, F_S, F_S])

# Arrows from ConsoleApp1 and WebApi into Opc.Ua; WebService has NO arrow (just note)
for k in ["ConsoleApp1", "WebApi"]:
    x, y, w, h = proj_pos[k]
    x1 = x + w + 6
    y1 = y + h / 2
    x2 = mid_x - 10
    y2 = mid_y + mid_h / 2
    arrow(d, x1, y1, x2, y2, color="#333", width=3)

# Dashed/red note from WebService
x, y, w, h = proj_pos["WebService"]
arrow(d, x + w + 6, y + h / 2, mid_x - 10, mid_y + mid_h / 2, color="#CC0000", width=2, dashed=True)
edge_label(d, x + w + 6, y + h / 2, mid_x - 10, mid_y + mid_h / 2, "no reference (yet)", color="#CC0000")

# Right column: NuGet dependency groups
right_x = 1180
groups = [
    ("OPC UA Stack",       ["OPCFoundation.NetStandard.Opc.Ua.*", "• Core, Client, ComplexTypes, Configuration"], 120, "#1F4E79"),
    ("JSON",               ["Newtonsoft.Json 13.0.3"],                                                                         280, "#555555"),
    ("Object Mapping",     ["AutoMapper 10.1.1"],                                                                              400, "#555555"),
    ("Crypto",             ["BouncyCastle.Cryptography 2.3.1"],                                                                520, "#555555"),
    ("DI (WebApi only)",   ["Ninject 3.3.x", "(in WebApi, not Opc.Ua)"],                                                       640, "#6A5ACD"),
]
grp_w, grp_h = 520, 80
for (title_g, lines, y, color) in groups:
    draw_box(d, right_x, y, grp_w, grp_h, color)
    shown = [title_g] + lines
    fonts = [F_B] + [F_T] * len(lines)
    draw_label(d, right_x, y, grp_w, grp_h, shown, color="white", fonts=fonts)

# Arrows from Opc.Ua to each group (fan-out)
for (title_g, lines, y, color) in groups:
    gx, gy = right_x - 10, y + grp_h / 2
    arrow(d, mid_x + mid_w + 6, mid_y + mid_h / 2, gx, gy, color="#888", width=2)

# Arrow from WebApi directly to Ninject group too (WebApi uses Ninject, not Opc.Ua library)
wx, wy, ww, wh = proj_pos["WebApi"]
ninject_y = 640
arrow(d, wx + ww + 6, wy + wh / 2, right_x - 10, ninject_y + grp_h / 2, color="#6A5ACD", width=2, dashed=True)

# Legend
ly = 820
d.line([(100, ly), (160, ly)], fill="#333", width=3); arrow(d, 160, ly, 180, ly, color="#333")
d.text((200, ly - 10), "project → library reference", fill="#333", font=F_T)
x0 = 560
for s in range(6):
    sx = x0 + s * 10
    d.line([(sx, ly), (sx + 5, ly)], fill="#888", width=2)
arrow(d, x0 + 60, ly, x0 + 80, ly, color="#888")
d.text((x0 + 100, ly - 10), "library → NuGet dependency", fill="#333", font=F_T)
x1 = 1100
for s in range(6):
    sx = x1 + s * 10
    d.line([(sx, ly), (sx + 5, ly)], fill="#CC0000", width=2)
d.text((x1 + 80, ly - 10), "missing / broken link (tech debt)", fill="#CC0000", font=F_T)

img.save(f"{OUTDIR}/module_diagram.png")
print("wrote module_diagram.png", os.path.getsize(f"{OUTDIR}/module_diagram.png"), "bytes")

# =========================================================
# 3) RUNTIME TOPOLOGY (§7.2)
# =========================================================
W, H = 1800, 1200
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)

title = "Figure 7.1 — ESSA Runtime Deployment Topology"
tw = d.textlength(title, font=F_TITLE)
d.text(((W - tw) / 2, 20), title, fill="#1F4E79", font=F_TITLE)

def zone(label, x, y, w, h, fill="#F2F6FB", stroke="#B5C7DD"):
    d.rounded_rectangle([x, y, x + w, y + h], radius=14, outline=stroke, width=2, fill=fill)
    d.text((x + 14, y + 10), label, fill="#1F4E79", font=F_H)

# Zone: Consumer (left)
zone("Consumer network", 80, 80, 380, 520)
# Zone: Server host (middle)
zone("Windows Server (IIS)", 540, 80, 720, 520)
# Zone: Plant VLAN (right)
zone("Plant / OT VLAN", 1340, 80, 380, 520)

# Clients
cx, cy = 120, 160
draw_box(d, cx, cy, 300, 80, "#2E8B57")
draw_label(d, cx, cy, 300, 80, ["BI / Dashboards", "Grafana • Power BI • scripts"], color="white", fonts=[F_H, F_S])

# Load balancer
lx, ly = 100, 300
draw_box(d, lx, ly, 340, 80, "#555555")
draw_label(d, lx, ly, 340, 80, ["Load Balancer / Proxy", "(optional) HTTPS termination"], color="white", fonts=[F_H, F_S])

# IIS + AppPool + Sites
iis_x, iis_y = 580, 140
draw_box(d, iis_x, iis_y, 640, 100, "#0F6FC6")
draw_label(d, iis_x, iis_y, 640, 100, ["IIS 10", "Windows features: ASP.NET 4.8, ISAPI, Static Content"], color="white", fonts=[F_H, F_T])

ap_x, ap_y = 600, 280
draw_box(d, ap_x, ap_y, 600, 100, "#1F4E79")
draw_label(d, ap_x, ap_y, 600, 100, ["AppPool: Essa", "Integrated pipeline • .NET CLR v4.0 • service-account identity"], color="white", fonts=[F_H, F_S])

site1_x, site1_y = 620, 420
draw_box(d, site1_x, site1_y, 260, 100, "#16A085")
draw_label(d, site1_x, site1_y, 260, 100, ["Site: Essa (/)", "WebApi on :443", "binding → OPC UA"], color="white", fonts=[F_H, F_S, F_S])

site2_x, site2_y = 920, 420
draw_box(d, site2_x, site2_y, 260, 100, "#6A5ACD")
draw_label(d, site2_x, site2_y, 260, 100, ["Site: Essa-WS (/ws)", "WebService (optional)", "(stub today)"], color="white", fonts=[F_H, F_S, F_S])

# OPC UA Server
opc_x, opc_y = 1380, 260
draw_box(d, opc_x, opc_y, 300, 120, "#B22222")
draw_label(d, opc_x, opc_y, 300, 120, ["OPC UA Server", "PLCs / SCADA / Historian", "opc.tcp:// port 4840 (prod)", "port 53530 (Prosys sim)"], color="white", fonts=[F_H, F_S, F_S, F_S])

# Side-car: Ops concerns on the server
cy2 = 650
zone("Host / Ops concerns", 540, cy2, 720, 200, fill="#FFF8E1", stroke="#E6B800")
items = [
    ("Windows Updates",                 600, cy2 + 50,  200),
    ("AV / EDR",                        820, cy2 + 50,  160),
    ("Event Log + IIS Logs",           1000, cy2 + 50,  240),
    ("Certificates (IIS + OPC UA)",     600, cy2 + 130, 300),
    ("Backup of IIS cfg + Web.config",  920, cy2 + 130, 320),
]
for (txt, x, y, w) in items:
    draw_box(d, x, y, w, 60, "#E6B800")
    draw_label(d, x, y, w, 60, [txt], color="white", fonts=[F_T])

# Connections
# Client → LB (HTTPS)
arrow(d, 270, 250, 270, 300, color="#333", width=3)
edge_label(d, 270, 250, 270, 300, "HTTPS")
# LB → IIS (HTTPS internal)
arrow(d, 420, 340, 580, 240, color="#333", width=3)
edge_label(d, 420, 340, 580, 240, "HTTPS")
# IIS → AppPool (vertical)
arrow(d, 900, 240, 900, 280, color="#333", width=3)
# AppPool → Sites
arrow(d, 750, 380, 750, 420, color="#333", width=3)
arrow(d, 1050, 380, 1050, 420, color="#333", width=3)
# AppPool / WebApi → OPC UA Server: straight horizontal from right edge of AppPool
arrow(d, 1200, 330, 1375, 320, color="#333", width=3)
edge_label(d, 1200, 330, 1375, 320, "opc.tcp:// 4840", offset=14)

# Legend
ly = 920
d.line([(100, ly), (160, ly)], fill="#333", width=3); arrow(d, 160, ly, 180, ly, color="#333")
d.text((200, ly - 10), "runtime call / network flow", fill="#333", font=F_T)
d.rectangle([620, ly - 12, 660, ly + 12], outline="#E6B800", width=2, fill="#FFF8E1")
d.text((670, ly - 10), "host / OS concern (Ops)", fill="#333", font=F_T)

img.save(f"{OUTDIR}/topology_diagram.png")
print("wrote topology_diagram.png", os.path.getsize(f"{OUTDIR}/topology_diagram.png"), "bytes")
