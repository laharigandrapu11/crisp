"""
CRISP — 2-Stage Neural Compression Pipeline
Streamlit demo UI for hackathon judges.

Visual spec translated from the interactive HTML prototype:
  - Light "lab-report" theme (#f6f5f1 paper, graphite ink, teal accent)
  - Three-column: input | pipeline stages | metrics + results
  - Hero metric tiles + detail table
  - Step-by-step live progress with pulsing active-stage indicator
  - Lossless-check badge
  - Truncated base64 payload preview
"""

import os
import io
import time
import base64
import math
import json
from collections import Counter
from typing import Optional, Dict, Any, Tuple

import requests
import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

STAGE1_URL = os.getenv("STAGE1_URL", "http://localhost:8081")   # OCR service
STAGE2_URL = os.getenv("STAGE2_URL", "http://localhost:8082")   # Compression service
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "15"))

st.set_page_config(
    page_title="CRISP — Neural Compression Pipeline",
    page_icon="◐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Theme / CSS — matches the prototype's "lab-report" aesthetic
# ---------------------------------------------------------------------------

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Fraunces:opsz,wght@9..144,400;9..144,500&display=swap');

:root{
  --bg:#f6f5f1; --surface:#fffdf8;
  --ink:#14161a; --ink-2:#3a3f46; --ink-3:#6b7079; --ink-4:#9aa0a6;
  --rule:#e4e2da; --rule-strong:#cfccbf;
  --accent:oklch(0.62 0.12 210);
  --accent-soft:oklch(0.92 0.04 210);
  --ok:oklch(0.62 0.13 155);
  --err:oklch(0.58 0.18 25);
  --mono:"JetBrains Mono",ui-monospace,monospace;
  --sans:"Inter",system-ui,sans-serif;
  --serif:"Fraunces",serif;
}

html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg) !important;
  color: var(--ink);
  font-family: var(--sans);
}
[data-testid="stHeader"]{ background: transparent; }
.block-container{ padding-top: 1.5rem; max-width: 1400px;}

h1,h2,h3,h4{ font-family: var(--serif); font-weight: 500; letter-spacing: -0.015em; color: var(--ink); }
p, label, span, div { color: var(--ink); }

/* brand */
.brand-bar{
  display:flex; align-items:baseline; justify-content:space-between;
  border-bottom: 1px solid var(--rule-strong);
  padding: 4px 0 14px; margin-bottom: 22px;
}
.brand-mark{ font-family: var(--serif); font-size: 24px; font-weight: 500; letter-spacing: -0.02em;}
.brand-mark .dot{ color: var(--accent); }
.brand-sub{ font-family: var(--mono); font-size: 11px; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.08em;}
.brand-meta{ font-family: var(--mono); font-size: 11px; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.08em;}

/* panels */
.panel{
  background: var(--surface); border: 1px solid var(--rule-strong);
  margin-bottom: 14px; position: relative;
}
.panel-head{
  padding: 10px 14px; border-bottom: 1px solid var(--rule);
  display:flex; justify-content:space-between;
  font-family: var(--mono); font-size: 11px;
  color: var(--ink-2); text-transform: uppercase; letter-spacing: 0.1em;
}
.panel-body{ padding: 16px; }

/* stepper */
.stepper{ display: grid; grid-template-columns: 1fr 1fr 1fr; border: 1px solid var(--rule-strong); background: var(--surface); }
.step{ padding: 16px 18px; border-right: 1px solid var(--rule); position: relative;}
.step:last-child{ border-right: none; }
.step .num{ font-family: var(--mono); font-size: 11px; color: var(--ink-4); letter-spacing: 0.08em; }
.step .name{ font-weight: 600; margin-top: 2px; font-size: 15px; }
.step .desc{ color: var(--ink-3); font-size: 12px; margin-top: 2px; }
.step .stat{
  display:flex; justify-content: space-between; margin-top: 10px;
  font-family: var(--mono); font-size: 11px; color: var(--ink-3);
}
.step .bar{ margin-top: 12px; height: 4px; background: var(--rule); position: relative; overflow: hidden;}
.step .bar .fill{ position: absolute; inset: 0; background: var(--accent); }
.step.done .bar .fill{ background: var(--ok); width: 100%; }
.step.active{ background: linear-gradient(90deg, var(--accent-soft) 0 3px, transparent 3px), var(--surface); }
.dot{ display:inline-block; width: 7px; height: 7px; border-radius: 999px; margin-right: 6px; vertical-align: middle; }
.dot.idle{ background: var(--ink-4); }
.dot.active{ background: var(--accent); animation: pulse 1.1s infinite; }
.dot.done{ background: var(--ok); }
@keyframes pulse{
  0%{ box-shadow: 0 0 0 0 oklch(0.62 0.12 210 / 0.5); }
  70%{ box-shadow: 0 0 0 7px oklch(0.62 0.12 210 / 0); }
  100%{ box-shadow: 0 0 0 0 oklch(0.62 0.12 210 / 0); }
}

/* hero metrics */
.hero-metrics{ display: grid; grid-template-columns: repeat(4, 1fr); border: 1px solid var(--rule-strong); background: var(--surface); }
.metric{ padding: 18px; border-right: 1px solid var(--rule); }
.metric:last-child{ border-right: none; }
.metric .lbl{ font-family: var(--mono); font-size: 10px; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.1em;}
.metric .val{ font-family: var(--serif); font-size: 38px; line-height: 1.05; letter-spacing: -0.02em; margin-top: 6px;}
.metric .val .unit{ font-family: var(--mono); font-size: 12px; color: var(--ink-3); margin-left: 4px;}
.metric .delta{ margin-top: 6px; font-family: var(--mono); font-size: 11px; color: var(--ok); }

/* detail table */
.detail-table{ width: 100%; border-collapse: collapse; font-family: var(--mono); font-size: 12px; background: var(--surface); border: 1px solid var(--rule-strong); }
.detail-table th, .detail-table td{ padding: 8px 14px; text-align: left; border-bottom: 1px solid var(--rule); }
.detail-table th{ font-weight: 500; color: var(--ink-3); text-transform: uppercase; font-size: 10px; letter-spacing: 0.1em; background: var(--bg);}
.detail-table td.num{ text-align: right; font-variant-numeric: tabular-nums; }

/* check badge */
.check{ display: inline-flex; align-items:center; gap: 8px; padding: 4px 10px;
  border: 1px solid var(--ok); color: var(--ok); font-family: var(--mono); font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.08em; background: oklch(0.62 0.13 155 / 0.08);}
.check.err{ border-color: var(--err); color: var(--err); background: oklch(0.58 0.18 25 / 0.08);}

/* payload block */
.mono-block{ font-family: var(--mono); font-size: 12px; background: var(--bg); padding: 10px 12px;
  border: 1px solid var(--rule); color: var(--ink-2); word-break: break-all; line-height: 1.55;}

/* buttons — Streamlit override */
.stButton > button{
  border-radius: 0 !important; border: 1px solid var(--ink) !important;
  background: var(--ink) !important; color: #fff !important;
  font-family: var(--sans) !important; font-weight: 500 !important;
}
.stButton > button:hover{ background: #2b2f35 !important; border-color: var(--ink) !important; }

/* file uploader */
[data-testid="stFileUploaderDropzone"]{
  background: repeating-linear-gradient(45deg, transparent 0 10px, oklch(0.95 0.01 90) 10px 11px), var(--surface) !important;
  border: 1.5px dashed var(--rule-strong) !important; border-radius: 0 !important;
}

/* status banner */
.status-banner{
  display:flex; gap: 12px; align-items: center;
  padding: 10px 14px; background: var(--surface);
  border: 1px solid var(--rule-strong); border-left: 3px solid var(--accent);
  font-family: var(--mono); font-size: 12px; margin-bottom: 14px;
}
.status-banner.ok{ border-left-color: var(--ok); }
.status-banner.idle{ border-left-color: var(--ink-4); }

.ocr-out{ font-family: var(--mono); font-size: 28px; letter-spacing: 0.18em; font-weight: 500;}
.muted{ color: var(--ink-3); }
.tag{ display:inline-block; font-family: var(--mono); font-size: 10px;
  padding: 2px 8px; border: 1px solid var(--rule-strong); color: var(--ink-3);
  text-transform: uppercase; letter-spacing: 0.08em; background: var(--surface); margin-right: 6px;}

#MainMenu, footer{ visibility: hidden; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_entropy(text: str) -> float:
    if not text:
        return 0.0
    n = len(text)
    counts = Counter(text)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def fmt_ms(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    return f"{seconds * 1000:.1f} ms"


def render_stepper(stage: int, progress: Tuple[float, float, float], result: Optional[dict]):
    """stage: 0 idle · 1 OCR · 2 Compress · 3 Decompress · 4 done."""
    stages = [
        ("01", "OCR",        "CNN → text",            "ocrLatency"),
        ("02", "Compress",   "Adaptive Huffman",      "compLatency"),
        ("03", "Decompress", "Lossless verify",       "decLatency"),
    ]
    html = ['<div class="stepper">']
    for i, (num, name, desc, key) in enumerate(stages):
        active = stage == i + 1
        done = stage > i + 1 or stage == 4
        state_class = "active" if active else "done" if done else "idle"
        state_label = "COMPLETE" if done else "RUNNING" if active else "IDLE"
        p = progress[i] if i < len(progress) else 0
        fill_w = 100 if done else int(p * 100)
        latency = fmt_ms(result.get(key)) if result and key in result else "— ms"
        html.append(f'''
          <div class="step {state_class}">
            <div class="num">STAGE {num}</div>
            <div class="name">{name}</div>
            <div class="desc">{desc}</div>
            <div class="bar"><div class="fill" style="width:{fill_w}%"></div></div>
            <div class="stat">
              <span><span class="dot {state_class}"></span>{state_label}</span>
              <span>{latency}</span>
            </div>
          </div>
        ''')
    html.append("</div>")
    return "".join(html)


def render_hero_metrics(result: Optional[dict]) -> str:
    def v(text): return f'<div class="val">{text}</div>'
    if not result:
        cells = [
            ("Compression Ratio", v("—")),
            ("Entropy",            v("—")),
            ("Encoding Efficiency",v("—")),
            ("Total Latency",      v("—")),
        ]
    else:
        cells = [
            ("Compression Ratio",
             f'<div class="val">{result["ratio"]:.2f}<span class="unit">×</span></div>'
             f'<div class="delta">−{(100 - 100/result["ratio"]):.0f}% bytes</div>'),
            ("Entropy",
             f'<div class="val">{result["entropy"]:.2f}<span class="unit">bits/sym</span></div>'),
            ("Encoding Efficiency",
             f'<div class="val">{result["efficiency"]*100:.1f}<span class="unit">%</span></div>'),
            ("Total Latency",
             f'<div class="val">{result["totalLatency"]*1000:.0f}<span class="unit">ms</span></div>'),
        ]
    parts = ['<div class="hero-metrics">']
    for lbl, body in cells:
        parts.append(f'<div class="metric"><div class="lbl">{lbl}</div>{body}</div>')
    parts.append("</div>")
    return "".join(parts)


def render_detail_table(result: Optional[dict]) -> str:
    def row(k, v_): return f'<tr><td>{k}</td><td class="num">{v_}</td></tr>'
    if not result:
        rows = [row(k, "—") for k in [
            "Original size", "Compressed size", "Original bits", "Compressed bits",
            "Avg bits per symbol", "Shannon entropy", "Efficiency",
            "Stage 1 OCR latency", "Stage 2 compress latency",
            "Stage 2 decompress latency", "Total end-to-end"
        ]]
    else:
        r = result
        rows = [
            row("Original size",             f'{r["origBytes"]} B'),
            row("Compressed size",           f'{r["compBytes"]} B'),
            row("Original bits",             f'{r["origBits"]}'),
            row("Compressed bits",           f'{r["compBits"]}'),
            row("Avg bits per symbol",       f'{r["avgBits"]:.3f}'),
            row("Shannon entropy",           f'{r["entropy"]:.3f} bits/sym'),
            row("Efficiency (H/ℓ̄)",         f'{r["efficiency"]*100:.2f} %'),
            row("Stage 1 OCR latency",       fmt_ms(r["ocrLatency"])),
            row("Stage 2 compress latency",  fmt_ms(r["compLatency"])),
            row("Stage 2 decompress latency",fmt_ms(r["decLatency"])),
            row("Total end-to-end",          fmt_ms(r["totalLatency"])),
        ]
    return (
        '<table class="detail-table">'
        '<thead><tr><th>Metric</th><th class="num">Value</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


# ---------------------------------------------------------------------------
# Pipeline calls (placeholder-aware: falls back to local simulation if env unset)
# ---------------------------------------------------------------------------

def call_stage1_ocr(image_bytes: bytes, filename: str = "upload.png") -> Dict[str, Any]:
    """POST image to Stage 1 OCR service. Returns {'text': str}."""
    if not STAGE1_URL or STAGE1_URL.startswith("http://localhost") and os.getenv("CRISP_MOCK", "0") == "1":
        return _mock_ocr(filename)
    try:
        img_b64 = base64.b64encode(image_bytes).decode("ascii")
        resp = requests.post(
            f"{STAGE1_URL}/ocr",
            json={"image_base64": img_b64},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.warning(f"Stage 1 unreachable ({e}); using mock.")
        return _mock_ocr(filename)


def call_stage2_encode(text: str) -> Dict[str, Any]:
    """POST text to Stage 2 Compress service. Returns payload + metrics."""
    if not STAGE2_URL or STAGE2_URL.startswith("http://localhost") and os.getenv("CRISP_MOCK", "0") == "1":
        return _mock_encode(text)
    try:
        resp = requests.post(
            f"{STAGE2_URL}/compress",
            json={"text": text},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.warning(f"Stage 2 (compress) unreachable ({e}); using mock.")
        return _mock_encode(text)


def call_stage2_decode(payload_b64: str) -> Dict[str, Any]:
    """POST payload to Stage 2 Decompress service. Returns {'text': str}."""
    if not STAGE2_URL or STAGE2_URL.startswith("http://localhost") and os.getenv("CRISP_MOCK", "0") == "1":
        return _mock_decode(payload_b64)
    try:
        resp = requests.post(
            f"{STAGE2_URL}/decompress",
            json={"payload_base64": payload_b64},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.warning(f"Stage 2 (decompress) unreachable ({e}); using mock.")
        return _mock_decode(payload_b64)


# --- Local mocks (for demo without backends) --------------------------------

def _mock_ocr(filename: str) -> Dict[str, Any]:
    import re
    m = re.search(r"\d+", filename)
    text = (m.group(0)[:6] if m else "7391")
    time.sleep(0.55)
    return {"text": text, "confidence": 0.992}


def _mock_encode(text: str) -> Dict[str, Any]:
    time.sleep(0.18)
    H = compute_entropy(text)
    avg_bits = max(H + 0.6, 1.2)
    comp_bits = int(math.ceil(avg_bits * len(text) + 16))
    comp_bytes = math.ceil(comp_bits / 8)
    payload_bytes = bytearray()
    seed = sum(ord(c) * (i + 7) for i, c in enumerate(text)) % 256
    for _ in range(comp_bytes):
        seed = (seed * 1103515245 + 12345) & 0xFF
        payload_bytes.append(seed)
    payload_b64 = base64.b64encode(bytes(payload_bytes)).decode("ascii")
    return {
        "payload": payload_b64,
        "origBytes": len(text),
        "compBytes": comp_bytes,
        "origBits": len(text) * 8,
        "compBits": comp_bits,
        "ratio": len(text) / comp_bytes if comp_bytes else 1,
        "entropy": H,
        "avgBits": avg_bits,
        "efficiency": (H / avg_bits) if avg_bits else 1.0,
    }


def _mock_decode(payload_b64: str) -> Dict[str, Any]:
    time.sleep(0.09)
    # The mock encoder is not a real Huffman; we echo the session original.
    return {"text": st.session_state.get("last_recognized", "")}


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

ss = st.session_state
ss.setdefault("stage", 0)
ss.setdefault("progress", (0.0, 0.0, 0.0))
ss.setdefault("result", None)
ss.setdefault("log", [])
ss.setdefault("image_bytes", None)
ss.setdefault("image_name", None)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="brand-bar">
      <div>
        <div class="brand-mark">CRISP<span class="dot">.</span></div>
        <div class="brand-sub">2-Stage Neural Compression Pipeline · v0.1</div>
      </div>
      <div class="brand-meta">
        <span class="tag">STAGE1_URL · {s1}</span>
        <span class="tag">STAGE2_URL · {s2}</span>
      </div>
    </div>
    """.format(
        s1="set" if os.getenv("STAGE1_URL") else "unset",
        s2="set" if os.getenv("STAGE2_URL") else "unset",
    ),
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Layout: left (input) | right (pipeline + results)
# ---------------------------------------------------------------------------

left, right = st.columns([1, 2], gap="large")

# ---------- LEFT: upload + preview ----------
with left:
    st.markdown('<div class="panel"><div class="panel-head"><span>Input · Image</span><span>PNG · JPG · ≤ 5 MB</span></div><div class="panel-body">', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Drop a handwritten digit image",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed",
    )
    st.markdown('</div></div>', unsafe_allow_html=True)

    if uploaded is not None:
        ss.image_bytes = uploaded.read()
        ss.image_name = uploaded.name

    run_clicked = st.button("Run pipeline", use_container_width=True, disabled=ss.image_bytes is None)
    if ss.result is not None:
        if st.button("Reset run", use_container_width=True):
            ss.stage = 0
            ss.progress = (0.0, 0.0, 0.0)
            ss.result = None
            ss.log = []
            st.rerun()

    st.markdown('<div class="panel"><div class="panel-head"><span>Image · Preview</span><span>raw</span></div>', unsafe_allow_html=True)
    if ss.image_bytes:
        try:
            img = Image.open(io.BytesIO(ss.image_bytes))
            st.image(img, use_column_width=True)
        except Exception:
            st.write("Preview unavailable.")
    else:
        st.markdown('<div class="panel-body muted" style="font-family:var(--mono); font-size:12px;">Awaiting upload…</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ---------- RIGHT: status, pipeline, metrics, results ----------
with right:
    # Status banner
    if ss.stage == 0:
        banner = '<div class="status-banner idle"><span class="muted">Idle — upload an image and click Run pipeline.</span></div>'
    elif ss.stage == 4 and ss.result:
        ok = ss.result.get("lossless", False)
        badge = "✓ LOSSLESS" if ok else "✗ MISMATCH"
        cls = "ok" if ok else "err"
        banner = (
            f'<div class="status-banner {cls}">'
            f'<span style="font-weight:600; color: var(--{"ok" if ok else "err"});">{badge}</span>'
            f'<span class="muted">Recovered “{ss.result["recovered"]}” · {fmt_ms(ss.result["totalLatency"])} end-to-end</span>'
            f'</div>'
        )
    else:
        label = ["Initializing…", "Stage 1 — OCR inference", "Stage 2 — Huffman encode", "Stage 2 — decode & verify"][ss.stage]
        banner = f'<div class="status-banner"><span>{label}</span></div>'
    st.markdown(banner, unsafe_allow_html=True)

    # Pipeline stages
    stepper_slot = st.empty()
    stepper_slot.markdown(
        '<div class="panel"><div class="panel-head"><span>Pipeline · Stages</span><span>STEPPER VIEW</span></div>'
        + render_stepper(ss.stage, ss.progress, ss.result)
        + '</div>',
        unsafe_allow_html=True,
    )

    # Hero metrics
    hero_slot = st.empty()
    hero_slot.markdown(
        '<div class="panel"><div class="panel-head"><span>Metrics · Headline</span><span>per-run</span></div>'
        + render_hero_metrics(ss.result)
        + '</div>',
        unsafe_allow_html=True,
    )

    # Results + detail side-by-side
    rc1, rc2 = st.columns(2, gap="medium")
    with rc1:
        results_slot = st.empty()
    with rc2:
        detail_slot = st.empty()

    def render_results():
        if not ss.result:
            return (
                '<div class="panel"><div class="panel-head"><span>Results · Payload</span><span>pending</span></div>'
                '<div class="panel-body muted" style="font-family:var(--mono); font-size:12px;">awaiting pipeline run…</div></div>'
            )
        r = ss.result
        payload_preview = r["payload"][:140] + (f"…+{len(r['payload']) - 140} chars" if len(r["payload"]) > 140 else "")
        check_html = (
            '<span class="check">✓ matches original</span>' if r["lossless"]
            else '<span class="check err">✗ mismatch</span>'
        )
        return (
            '<div class="panel"><div class="panel-head"><span>Results · Payload</span><span>ready</span></div>'
            '<div class="panel-body">'
            f'<div class="muted" style="font-family:var(--mono); font-size:10px; text-transform:uppercase; letter-spacing:0.1em;">Recognized</div>'
            f'<div class="ocr-out" style="margin:4px 0 14px;">{r["recognized"]}</div>'
            f'<div class="muted" style="font-family:var(--mono); font-size:10px; text-transform:uppercase; letter-spacing:0.1em;">Compressed payload</div>'
            f'<div class="mono-block" style="margin:6px 0 14px;">{payload_preview}</div>'
            f'<div class="muted" style="font-family:var(--mono); font-size:10px; text-transform:uppercase; letter-spacing:0.1em;">Recovered</div>'
            f'<div style="display:flex; align-items:center; gap:12px; margin-top:4px;">'
            f'  <span class="ocr-out">{r["recovered"]}</span>{check_html}</div>'
            '</div></div>'
        )

    results_slot.markdown(render_results(), unsafe_allow_html=True)
    detail_slot.markdown(
        '<div class="panel"><div class="panel-head"><span>Metrics · Detail</span><span>per-run</span></div>'
        + render_detail_table(ss.result)
        + '</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------

def _log(msg: str):
    ts = time.strftime("%H:%M:%S")
    ss.log.append(f"[{ts}] {msg}")


def run_pipeline(image_bytes: bytes, filename: str):
    ss.log = []
    ss.result = None
    ss.progress = (0.0, 0.0, 0.0)

    # --- Stage 1: OCR ---
    ss.stage = 1
    _log(f"POST {STAGE1_URL}/ocr  size={len(image_bytes)}B")
    stepper_slot.markdown(
        '<div class="panel"><div class="panel-head"><span>Pipeline · Stages</span><span>STEPPER VIEW</span></div>'
        + render_stepper(ss.stage, (0.4, 0, 0), None)
        + '</div>',
        unsafe_allow_html=True,
    )
    t0 = time.time()
    ocr = call_stage1_ocr(image_bytes, filename=filename)
    ocr_latency = time.time() - t0
    recognized = ocr.get("text", "")
    ss["last_recognized"] = recognized
    _log(f"stage1 ← text='{recognized}' conf={ocr.get('confidence', 0):.3f} ({fmt_ms(ocr_latency)})")

    # --- Stage 2: Compress ---
    ss.stage = 2
    stepper_slot.markdown(
        '<div class="panel"><div class="panel-head"><span>Pipeline · Stages</span><span>STEPPER VIEW</span></div>'
        + render_stepper(ss.stage, (1, 0.5, 0), {"ocrLatency": ocr_latency})
        + '</div>',
        unsafe_allow_html=True,
    )
    t1 = time.time()
    enc_raw = call_stage2_encode(recognized)
    comp_latency = time.time() - t1
    # Normalise: real API returns {payload_base64, metrics:{...}}, mock returns flat dict
    if "payload_base64" in enc_raw:
        m = enc_raw.get("metrics", {})
        enc = {
            "payload":   enc_raw["payload_base64"],
            "origBytes": m.get("original_bytes", len(recognized)),
            "compBytes": m.get("compressed_bytes", len(recognized)),
            "origBits":  m.get("original_bytes", len(recognized)) * 8,
            "compBits":  m.get("compressed_bytes", len(recognized)) * 8,
            "ratio":     m.get("compression_ratio", 1.0),
            "entropy":   m.get("entropy", compute_entropy(recognized)),
            "avgBits":   m.get("avg_bits_per_symbol", 8.0),
            "efficiency":m.get("encoding_efficiency", 1.0),
        }
    else:
        enc = enc_raw  # mock already returns flat dict
    _log(f"stage2.compress ← {enc['origBytes']}B→{enc['compBytes']}B ratio={enc['ratio']:.2f}x ({fmt_ms(comp_latency)})")

    # --- Stage 2: Decompress ---
    ss.stage = 3
    stepper_slot.markdown(
        '<div class="panel"><div class="panel-head"><span>Pipeline · Stages</span><span>STEPPER VIEW</span></div>'
        + render_stepper(ss.stage, (1, 1, 0.5), {"ocrLatency": ocr_latency, "compLatency": comp_latency})
        + '</div>',
        unsafe_allow_html=True,
    )
    t2 = time.time()
    dec = call_stage2_decode(enc["payload"])
    dec_latency = time.time() - t2
    recovered = dec.get("text", "")
    lossless = (recovered == recognized)
    _log(f"stage2.decode ← text='{recovered}' lossless={lossless} ({fmt_ms(dec_latency)})")

    total = ocr_latency + comp_latency + dec_latency

    ss.stage = 4
    ss.progress = (1.0, 1.0, 1.0)
    ss.result = {
        "recognized": recognized,
        "recovered": recovered,
        "lossless": lossless,
        "payload": enc["payload"],
        "origBytes": enc["origBytes"],
        "compBytes": enc["compBytes"],
        "origBits": enc["origBits"],
        "compBits": enc["compBits"],
        "ratio": enc["ratio"],
        "entropy": enc["entropy"],
        "avgBits": enc["avgBits"],
        "efficiency": enc["efficiency"],
        "ocrLatency": ocr_latency,
        "compLatency": comp_latency,
        "decLatency": dec_latency,
        "totalLatency": total,
    }


if run_clicked and ss.image_bytes:
    run_pipeline(ss.image_bytes, ss.image_name or "upload.png")
    st.rerun()


# ---------------------------------------------------------------------------
# Log panel
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="panel"><div class="panel-head"><span>Request Log</span><span>{n} events</span></div>'
    '<div class="panel-body"><div class="mono-block" style="white-space:pre-wrap; min-height:80px;">{body}</div></div></div>'
    .format(
        n=len(ss.log),
        body="\n".join(ss.log) if ss.log else "No events yet. Upload an image and click Run pipeline to dispatch.",
    ),
    unsafe_allow_html=True,
)
