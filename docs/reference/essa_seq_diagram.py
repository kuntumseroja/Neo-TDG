"""Render a sequence diagram PNG for the ESSA data-flow section."""
from PIL import Image, ImageDraw, ImageFont
import os

# ---------- layout ----------
WIDTH = 2100
HEIGHT = 1900
MARGIN_X = 120
MARGIN_TOP = 80
LANE_Y_TOP = 150           # where lane heads sit
LANE_Y_BOTTOM = HEIGHT - 80
STEP = 68                  # vertical distance between messages

# participants (name, x) — we compute x below
PARTICIPANTS = [
    ("HTTP Client\n(BI / Dashboard)", "#1F4E79"),
    ("ASP.NET\nWeb API", "#0F6FC6"),
    ("Ninject\n(DI)", "#6A5ACD"),
    ("OpcController", "#2E8B57"),
    ("HistoryRawData\n(IHistoryRawData)", "#C05621"),
    ("ServerConnector", "#A0522D"),
    ("OPC UA Server", "#B22222"),
]
N = len(PARTICIPANTS)
usable = WIDTH - 2 * MARGIN_X
spacing = usable / (N - 1)
lane_x = [int(MARGIN_X + i * spacing) for i in range(N)]

# ---------- image / fonts ----------
img = Image.new("RGB", (WIDTH, HEIGHT), "white")
draw = ImageDraw.Draw(img)

def load_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()

F_TITLE = load_font(30, bold=True)
F_PART  = load_font(18, bold=True)
F_MSG   = load_font(17)
F_MSG_B = load_font(17, bold=True)
F_NUM   = load_font(15, bold=True)
F_NOTE  = load_font(16, bold=True)

# ---------- title ----------
title = "ESSA — End-to-End Sequence: POST /opc-ua-api/history-raw-data"
tw = draw.textlength(title, font=F_TITLE)
draw.text(((WIDTH - tw) / 2, 20), title, fill="#1F4E79", font=F_TITLE)

# ---------- participant boxes + lifelines ----------
BOX_H = 64
for (label, color), x in zip(PARTICIPANTS, lane_x):
    # top box
    lines = label.split("\n")
    text_w = max(draw.textlength(ln, font=F_PART) for ln in lines)
    box_w = int(max(text_w + 30, 150))
    x0 = x - box_w // 2
    y0 = LANE_Y_TOP - BOX_H // 2
    draw.rounded_rectangle([x0, y0, x0 + box_w, y0 + BOX_H], radius=8, fill=color, outline=color)
    # multi-line centered text
    line_h = 22
    total_h = line_h * len(lines)
    for i, ln in enumerate(lines):
        lw = draw.textlength(ln, font=F_PART)
        draw.text((x - lw / 2, y0 + (BOX_H - total_h) / 2 + i * line_h), ln, fill="white", font=F_PART)
    # lifeline
    draw.line([(x, y0 + BOX_H), (x, LANE_Y_BOTTOM)], fill="#888888", width=1)
    # repeat box at bottom for readability
    x0b, y0b = x - box_w // 2, LANE_Y_BOTTOM
    draw.rounded_rectangle([x0b, y0b, x0b + box_w, y0b + BOX_H], radius=8, fill=color, outline=color)
    for i, ln in enumerate(lines):
        lw = draw.textlength(ln, font=F_PART)
        draw.text((x - lw / 2, y0b + (BOX_H - total_h) / 2 + i * line_h), ln, fill="white", font=F_PART)

# ---------- arrow helpers ----------
def arrow(y, i_from, i_to, label, dashed=False, num=None, note_above=None):
    x1 = lane_x[i_from]
    x2 = lane_x[i_to]
    color = "#333333"
    # message label
    if label:
        # position above arrow
        lw = draw.textlength(label, font=F_MSG)
        lx = min(x1, x2) + (abs(x2 - x1) - lw) / 2
        # split long labels
        draw.text((lx, y - 22), label, fill=color, font=F_MSG)
    # arrow line
    if dashed:
        # manual dashed line
        length = abs(x2 - x1)
        steps = int(length / 10)
        for s in range(steps):
            sx = x1 + (x2 - x1) * s / steps
            ex = x1 + (x2 - x1) * (s + 0.5) / steps
            draw.line([(sx, y), (ex, y)], fill=color, width=2)
    else:
        draw.line([(x1, y), (x2, y)], fill=color, width=2)
    # arrowhead
    head = 10
    if x2 > x1:
        draw.polygon([(x2, y), (x2 - head, y - 6), (x2 - head, y + 6)], fill=color)
    else:
        draw.polygon([(x2, y), (x2 + head, y - 6), (x2 + head, y + 6)], fill=color)
    # step number circle — placed clearly LEFT of the arrow's starting lane, aligned with line
    if num is not None:
        cx = min(x1, x2) - 40
        cy = y
        r = 13
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#0F6FC6", outline="#0F6FC6")
        tw = draw.textlength(str(num), font=F_NUM)
        draw.text((cx - tw / 2, cy - 10), str(num), fill="white", font=F_NUM)

def self_note(y, i, label, num=None):
    # small self-call loop
    x = lane_x[i]
    draw.line([(x, y), (x + 60, y)], fill="#333333", width=2)
    draw.line([(x + 60, y), (x + 60, y + 24)], fill="#333333", width=2)
    draw.line([(x + 60, y + 24), (x + 10, y + 24)], fill="#333333", width=2)
    draw.polygon([(x, y + 24), (x + 12, y + 18), (x + 12, y + 30)], fill="#333333")
    # label
    draw.text((x + 70, y), label, fill="#333333", font=F_MSG)
    if num is not None:
        cx, cy = x - 28, y + 12
        r = 14
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#0F6FC6", outline="#0F6FC6")
        tw = draw.textlength(str(num), font=F_NUM)
        draw.text((cx - tw / 2, cy - 10), str(num), fill="white", font=F_NUM)

def loop_frame(y_top, y_bot, label):
    # box spanning controller → OPC UA server lanes
    x0 = lane_x[3] - 40
    x1 = lane_x[6] + 60
    # dashed rectangle
    draw.rectangle([x0, y_top, x1, y_bot], outline="#0F6FC6", width=2)
    # label tab
    tw = draw.textlength(label, font=F_NOTE)
    draw.rounded_rectangle([x0, y_top - 22, x0 + tw + 24, y_top + 8], radius=4, fill="#0F6FC6")
    draw.text((x0 + 12, y_top - 18), label, fill="white", font=F_NOTE)

# ---------- messages ----------
y = LANE_Y_TOP + 70

arrow(y, 0, 1, "POST /opc-ua-api/history-raw-data  [ {Start, End, TagId} ]", num=1); y += STEP
self_note(y, 1, "Deserialize → ReadRawCriteriaCollectionDto", num=2); y += STEP + 4
arrow(y, 1, 2, "Resolve OpcController", num=3); y += STEP
arrow(y, 2, 1, "new HistoryRawData(), new CurrentRawData()  →  OpcController", dashed=True); y += STEP
arrow(y, 1, 3, "BulkHistoryRawData(dto)", num=4); y += STEP

# loop frame
loop_top = y - 6
arrow(y, 3, 4, "Read(start, end, tagId)", num=5); y += STEP
arrow(y, 4, 5, "CreateSession(serverUrl, useSecurity)", num="5a"); y += STEP
arrow(y, 5, 6, "opc.tcp:// handshake + endpoint select", num="5b"); y += STEP
arrow(y, 6, 5, "Session + endpoint", dashed=True); y += STEP
arrow(y, 5, 4, "Session", dashed=True); y += STEP
arrow(y, 4, 6, "Browse(ObjectsFolder)  — find Tag by Id", num="5c"); y += STEP
arrow(y, 6, 4, "ReferenceDescription", dashed=True); y += STEP
arrow(y, 4, 6, "HistoryRead(ReadRawModifiedDetails)", num="5d"); y += STEP
arrow(y, 6, 4, "HistoryReadResultCollection", dashed=True); y += STEP
self_note(y, 4, "AutoMapper: DataValue → RawDataValue", num="5e"); y += STEP + 4
arrow(y, 4, 3, "TagHistoryRawData (Name, NodeId, Id, RawDataValues[])", dashed=True, num="5f"); y += STEP
loop_bot = y - 16
loop_frame(loop_top, loop_bot, "loop  for each criteria item in dto")

y += 10
arrow(y, 3, 1, "Ok(tags)", dashed=True, num=6); y += STEP
arrow(y, 1, 0, "200 OK + JSON payload", dashed=True, num=7); y += STEP

# ---------- legend ----------
ly = LANE_Y_BOTTOM + BOX_H + 18
# solid
draw.line([(MARGIN_X, ly + 8), (MARGIN_X + 40, ly + 8)], fill="#333333", width=2)
draw.polygon([(MARGIN_X + 40, ly + 8), (MARGIN_X + 32, ly + 4), (MARGIN_X + 32, ly + 12)], fill="#333333")
draw.text((MARGIN_X + 52, ly - 2), "synchronous call", fill="#333333", font=F_MSG)
# dashed
x0 = MARGIN_X + 260
for s in range(8):
    sx = x0 + s * 5
    draw.line([(sx, ly + 8), (sx + 2.5, ly + 8)], fill="#333333", width=2)
draw.polygon([(x0 + 40, ly + 8), (x0 + 32, ly + 4), (x0 + 32, ly + 12)], fill="#333333")
draw.text((x0 + 52, ly - 2), "return value", fill="#333333", font=F_MSG)
# step number
draw.ellipse([MARGIN_X + 470, ly - 6, MARGIN_X + 498, ly + 22], fill="#0F6FC6")
tw = draw.textlength("n", font=F_NUM)
draw.text((MARGIN_X + 478, ly - 2), "n", fill="white", font=F_NUM)
draw.text((MARGIN_X + 510, ly - 2), "step number (matches runbook)", fill="#333333", font=F_MSG)
# loop box
draw.rectangle([MARGIN_X + 820, ly - 6, MARGIN_X + 870, ly + 22], outline="#0F6FC6", width=2)
draw.text((MARGIN_X + 880, ly - 2), "loop / iteration frame", fill="#333333", font=F_MSG)

# save
out = '/sessions/confident-admiring-bohr/mnt/outputs/analysis/sequence_diagram.png'
img.save(out)
print("wrote", out, os.path.getsize(out), "bytes")
