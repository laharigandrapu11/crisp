# Handoff: CRISP — 2-Stage Neural Compression Pipeline Demo UI

## Overview
CRISP is a hackathon demo UI for a two-stage neural compression pipeline deployed on GCP Cloud Run. The user uploads a noisy handwritten digit image, and the app walks them through:

1. **Stage 1 — OCR:** a CNN reads the image and returns recognized text (e.g. "7391").
2. **Stage 2 — Compress:** adaptive Huffman encoding compresses the text; returns a base64 payload + metrics.
3. **Stage 2 — Decompress:** recovers the original text from the payload; asserts a lossless round-trip.

The UI is a single-page console with a left "input" column (upload + sample images + preview) and a right "results" column (status banner, live pipeline stages, headline metrics, results payload, detailed metrics table).

## About the Design Files
The files in this bundle are **design references created in HTML/React + a parallel Streamlit `app.py`**. The HTML files are interactive prototypes showing the intended look, behavior, and interaction — they are NOT production code to ship directly.

The target deployment is **Streamlit on GCP Cloud Run** — `app.py` is the canonical implementation you should extend. The HTML prototype exists as the visual spec. If there is no codebase yet, implement the design in Streamlit (the app.py is already a strong starting point). If the team has moved to a different framework (FastAPI + React, etc.), recreate the same layout and visual system using that stack's conventions.

## Fidelity
**High-fidelity (hifi).** The prototype and Streamlit app share a complete design system — exact colors, typography, spacing, border-radii, and component styles. Match pixel-for-pixel when implementing.

## Screens / Views

There is a single screen — the **Pipeline Console**. Below is a full breakdown of its regions.

### 1. Masthead (top)
- **Layout:** full-width, sticky-top, 1600px max-width inner row, `padding: 18px 32px`. `border-bottom: 1px solid var(--rule-strong)`.
- **Left — Brand:** `CRISP.` in Fraunces 500, 22px, letter-spacing -0.02em. The trailing period uses the teal accent color. Secondary line in JetBrains Mono 11px uppercase: "2-STAGE NEURAL COMPRESSION PIPELINE · V0.1".
- **Right — Service status pills:** JetBrains Mono 11px uppercase, 0.08em tracking, ink-3 color. First pill has a green pulsing dot (`.live-dot`) + "SERVICES ONLINE". Followed by plain labels "STAGE1 · US-CENTRAL1" and "STAGE2 · US-CENTRAL1".

### 2. Page Header
- **Layout:** below masthead, inside the 1600px container. Flex-row justify-between, baseline-aligned.
- **Left title:** "Pipeline Console" in Fraunces 500, 22px, followed by a muted one-line description ("Upload a noisy handwritten digit image. CRISP runs OCR, compresses the recognized text via adaptive Huffman coding, and verifies lossless recovery.")

### 3. Two-Column Grid
- `grid-template-columns: 380px 1fr`, `gap: 20px`.
- Collapses to a single column at `max-width: 1080px`.

### 4. LEFT column (Input)
Stacked, `gap: 20px`.

**A. Upload panel**
- Panel head: title "Upload image" (sans 13px/600), meta "PNG · JPG · ≤ 5 MB" (mono 10px uppercase ink-4).
- Panel body contains:
  - **Dropzone:** 1.5px dashed `--rule-strong`, 6px radius, 28px/22px padding, centered. Contains a 40px circle glyph "↑", "Drop image, or click to browse" (sans 500), "28×28 grayscale or larger, handwritten digits" (sub, ink-3), "ACCEPTED · IMAGE/PNG, IMAGE/JPEG" (mono 10px uppercase ink-4).
  - **Hover/drag:** border turns teal; background becomes `--accent-soft`.
  - **"Sample images"** label (mono 10px uppercase ink-3), followed by a 4-column grid of square tiles (1:1 aspect, 1px rule border, 4px radius, 3px padding). Each tile renders a noisy-digit SVG with a black `#0c0d10` background and handwritten paths in warm white. Tiles show a "01"/"02"/"03"/"04" corner label (mono 9px ink-4). Selected tile gets a black border + 1px black outer shadow.
  - **Run pipeline button:** full-width, primary (teal `--accent` background, white text), 6px radius, 11px/16px padding, sans 500. Right-side `↵` kbd hint.
  - If a result exists, a tiny "reset run" text link in mono 11px ink-3.

**B. Preview panel**
- Panel head: "Preview" / "raw input".
- Body: fixed-height 140px, `#0c0d10` dark background, centered noisy-digit SVG rendered at ~60% width. Top-left badge "STAGE 0 · RAW" on semi-transparent white pill (mono 10px uppercase).

### 5. RIGHT column (Results)
Stacked, `gap: 20px`.

**A. Status banner**
- Single row, flex gap 12px, mono 12px. 1px rule-border, 3px left-border accent.
- **Idle:** grey left-border, muted "Idle — choose a sample or drop an image to begin."
- **Running:** teal left-border, live-dot + current stage label ("Stage 1 — OCR inference" / "Stage 2 — Huffman encode" / "Stage 2 — decode & verify").
- **Done:** green left-border, green "✓ LOSSLESS" + muted "Recovered '…' matches original · N ms end-to-end".

**B. Pipeline stages panel**
- Panel head: "Pipeline" / "stepper view" (meta reflects the current Tweaks variant).
- Three variants available (switchable via Tweaks panel): **Stepper**, **Network**, **Timeline**. Default: **Stepper**.

#### Stepper variant (default)
- `grid-template-columns: 1fr 1fr 1fr`, each cell separated by 1px rules.
- Per cell: `padding: 20px 22px`, uppercase mono label "STAGE 01/02/03", bold 15px name ("OCR", "Compress", "Decompress"), mono 12px ink-3 description ("CNN → text", "Adaptive Huffman", "Lossless verify"), a 4px progress bar (background `--rule`, fill teal or green when done), and a `flex` stat row with a state-dot + status label ("IDLE" / "RUNNING" / "COMPLETE") on the left and stage latency (mono) on the right.
- Active cell: teal 3px left inner stripe + shimmer overlay animating across the progress bar.
- Dot states: `--ink-4` idle, teal pulsing ring when active, solid green when done.

#### Network variant
- 280px-tall panel with a grid-paper background. SVG edges connect 5 nodes:
  INPUT → STAGE 01 → STAGE 02A → STAGE 02B → VERIFY.
- Nodes are 136px wide, 6px radius, 1px rule border. Input/Verify are dashed. Active nodes glow with `box-shadow: 0 0 0 3px var(--accent-soft)` + teal border.
- Running edges draw a moving teal circle along the line.

#### Timeline variant
- Two-column: 40px axis column (dashed vertical rule) + stacked step list.
- Each step: dot on axis (grey/teal pulsing/green), sans 500 name, right-aligned mono latency, muted description. If the stage completed, shows a mono payload snippet in a grey block (e.g. `recognized = "7391" · conf=0.992`, `<base64 payload snippet>…`, `recovered = "7391" · match=true`).

**C. Hero metrics**
- Panel head "Key metrics" (empty meta).
- `grid-template-columns: repeat(4, 1fr)` with 1px dividers.
- Per tile: mono 10px uppercase label, Fraunces 38-40px numeric value with small mono unit, a green "−X% bytes" delta under Compression Ratio.
- Four tiles: **Compression Ratio** (e.g. `2.47×`), **Entropy** (`bits/sym`), **Encoding Efficiency** (`%`), **Total Latency** (`ms`).
- Before a result exists, values show `—`.

**D. Results + Detailed metrics (two-col, `1fr 1fr`, gap 20px)**

*Results panel (left):*
- Panel head "Results" / "ready"|"pending".
- Three rows using a `result-grid` (160px label column / 1fr value column, 14px row gap, 18px column gap):
  1. **Recognized:** large mono-spaced output (28px, 0.18em letter-spacing, 500 weight) — e.g. `7391`.
  2. **Compressed payload:** mono 12px inside a bordered grey `--bg` block, 4px radius. Shows first 140 chars, then "…+N chars" in ink-4 if truncated.
  3. **Recovered:** same big mono output + a pill badge "✓ matches original" (1px green border, green text, tinted background, mono 10px uppercase, 999px radius).
- Divider hairline.
- **Byte comparison:** two rows, each `80px 1fr 80px` grid: mono uppercase label / solid fill bar (10px tall, 999px radius, `--bg` track, graphite/teal fill, 0.4s width transition) / right-aligned byte count.

*Detailed metrics panel (right):*
- Panel head "Detailed metrics" / "per-run".
- Table: `detail-table`. Head row is mono 10px uppercase ink-3 on `--bg`. Body rows are mono 12px, 8px/14px padding, 1px bottom rule per row (none on last). Right column is tabular-nums, right-aligned.
- Rows: Original size (B), Compressed size (B), Avg bits per symbol, Shannon entropy, Efficiency (H/ℓ̄), Stage 1 OCR latency, Stage 2 compress latency, Stage 2 decompress latency, Total end-to-end (bold ink).

### 6. Footer
- Max-width 1600px, `margin: 30px auto 40px`, `border-top: 1px solid var(--rule)`. Two-side flex row, mono 10px uppercase ink-4 letter-spacing 0.1em:
  - Left: "CRISP · neural compression · hackathon build"
  - Right: "GCP Cloud Run · streamlit · tf.keras · adaptive huffman"

### 7. Tweaks panel (optional, hidden by default)
- Floating bottom-right card, 280px wide, 8px radius, 1px rule border, drop-shadow.
- Head: "Tweaks" (left) and "CRISP" (right), mono 11px uppercase.
- Body sections (each is a `tweak-row` with a mono uppercase label + segmented `seg` control):
  1. **Pipeline Visual:** Stepper / Network / Timeline
  2. **Accent:** Teal / Indigo / Ochre / Graphite
  3. **Request Log:** Visible / Hidden (optional — current build omits the log panel)

## Interactions & Behavior

- **File upload:** click the dropzone or drag an image onto it. Also accepts click-to-select through a hidden `<input type="file" accept="image/png,image/jpeg">`.
- **Sample selection:** clicking any sample tile replaces the current selection and clears the uploaded filename.
- **Run pipeline:** disabled while a run is in progress. Once clicked:
  1. Set `stage=1`, POST image to `STAGE1_URL/predict`, await `{text, confidence}`.
  2. Set `stage=2`, POST recognized text to `STAGE2_URL/encode`, await `{payload, origBytes, compBytes, ratio, entropy, avgBits, efficiency, ...}`.
  3. Set `stage=3`, POST payload to `STAGE2_URL/decode`, await `{text}`.
  4. Set `stage=4`, mark `lossless = (recovered === recognized)`, show result.
- **Reset run:** clears result, returns to idle.
- **Stage progress animation:** the active stage's progress bar fills linearly over the measured duration; a shimmer gradient moves across it. The state-dot pulses teal. Non-active stages show "IDLE" / "COMPLETE". Use a ~600ms min duration per stage for perceived responsiveness even when backends respond fast.
- **Lossless check:** renders a green `✓ matches original` pill on success, red `✗ mismatch` on failure.
- **Tweaks toggle:** the panel listens for `{type: "__activate_edit_mode"}` / `{type: "__deactivate_edit_mode"}` postMessages from the hosting frame; it posts `{type: "__edit_mode_available"}` and `{type: "__edit_mode_set_keys", edits: {...}}` back. In Streamlit, replace with a sidebar toggle (`st.sidebar.radio`).

## State Management

In the React prototype:
```
state = {
  running: boolean,
  stage: 0 | 1 | 2 | 3 | 4,      // 0 idle, 4 done
  progress: [ocrPct, compPct, decPct],
  result: null | {
    recognized, recovered, lossless,
    payload,                      // base64 string
    origBytes, compBytes, origBits, compBits,
    ratio, entropy, avgBits, efficiency,
    ocrLatency, compLatency, decLatency, totalLatency   // seconds
  },
  log: string[]                   // optional request log
}
```

In Streamlit, the same shape is held in `st.session_state.result` and stage progression is driven by sequential blocking calls + `st.rerun()`.

## Design Tokens

### Colors (light "lab-report" palette)
```
--bg:            #f6f5f1              /* warm paper */
--surface:       #fffdf8              /* card background */
--ink:           #14161a              /* primary text */
--ink-2:         #3a3f46              /* secondary text */
--ink-3:         #6b7079              /* tertiary text / muted */
--ink-4:         #9aa0a6              /* quaternary / placeholders */
--rule:          #e4e2da              /* hairline dividers */
--rule-strong:   #cfccbf              /* stronger borders */
--accent:        oklch(0.62 0.12 210) /* teal primary */
--accent-soft:   oklch(0.92 0.04 210) /* tinted teal bg */
--ok:            oklch(0.62 0.13 155) /* success green */
--warn:          oklch(0.70 0.14 75)  /* amber */
--err:           oklch(0.58 0.18 25)  /* error red */
```

Alternate accents (selectable via Tweaks, lightness/chroma held constant, hue only varies):
- Indigo `oklch(0.55 0.15 275)`
- Ochre `oklch(0.68 0.13 75)`
- Graphite `oklch(0.30 0.02 260)`

### Typography
- **Sans (UI):** Inter 400/500/600/700. Base body 14px, line-height 1.45, letter-spacing -0.003em.
- **Mono (data, labels, latencies):** JetBrains Mono 400/500/600. Labels are 10–11px uppercase, tracking 0.08–0.1em.
- **Serif (hero numbers, titles):** Fraunces 400/500. Used for "Pipeline Console" title (22px), "CRISP." brand (22px, 500), and hero metric values (38–40px, -0.02em tracking, 1.05 line-height).

### Spacing
- Container padding: 32px horizontal, 24px top.
- Panel body padding: 18px 20px 20px.
- Panel head padding: 16px 20px 10px.
- Vertical gap between panels: 20px.
- Two-column gaps: 20px.

### Radii
- Cards/panels: 6px.
- Dropzone: 6px.
- Sample tile: 4px.
- Mono text blocks: 4px.
- Tweaks panel: 8px.
- Pills / badges / bar tracks: 999px.

### Shadows
- Tweaks panel: `0 20px 48px -18px rgba(0,0,0,0.18)`.
- Otherwise shadows are avoided in favor of 1px rule borders.

### Motion
- Pulse animation on live-dot (1.8s infinite, `box-shadow` scale).
- Teal pulse on active stage dot (1.1s infinite).
- Shimmer across active progress bar (1.2s linear infinite gradient translate).
- Byte comparison bar width transitions 0.4s ease.

## Assets
- **Fonts:** Google Fonts — Inter, JetBrains Mono, Fraunces.
- **Digit glyphs:** hand-authored SVG paths for digits 0–9, inlined in `src/samples.jsx` (`DigitStrokes`). The `NoisyDigit` component composes them with deterministic jitter, scan-lines, and noise dots to look handwritten.
- **Icons:** none — all glyphs are either Unicode (↑, ✓, ↵) or SVG shapes.
- No raster image assets are included.

## Backend Integration

`app.py` expects two services, each reachable via env var:

- `STAGE1_URL` — OCR service. Endpoint: `POST /predict` with multipart form `image=(filename, bytes, "image/png")`. Response JSON: `{"text": "7391", "confidence": 0.992}`.
- `STAGE2_URL` — compression service.
  - `POST /encode` with JSON `{"text": "7391"}`. Response: `{"payload": "<base64>", "origBytes": 4, "compBytes": 3, "origBits": 32, "compBits": 18, "ratio": 1.33, "entropy": 1.98, "avgBits": 2.12, "efficiency": 0.93}`.
  - `POST /decode` with JSON `{"payload": "<base64>"}`. Response: `{"text": "7391"}`.

If the env var is unset and `CRISP_MOCK=1`, the Streamlit app falls back to local mock implementations for demos.

## Files in this bundle

- `index.html` — entry point for the React prototype.
- `styles.css` — all design tokens + component styles.
- `src/app.jsx` — main App composition.
- `src/samples.jsx` — noisy-digit SVG renderer + sample set.
- `src/pipeline.jsx` — simulated pipeline runner (replace with real fetches when wiring up).
- `src/visualizations.jsx` — Stepper / Network / Timeline stage views.
- `src/metrics.jsx` — HeroMetrics, DetailTable, BytesBar components.
- `src/tweaks.jsx` — Tweaks panel + host postMessage protocol.
- `app.py` — Streamlit implementation (canonical target). Mirrors the HTML visual system via injected `<style>` block.

Run the Streamlit app:
```
pip install streamlit requests pillow
STAGE1_URL=https://... STAGE2_URL=https://... streamlit run app.py
# or for local demo without backends:
CRISP_MOCK=1 streamlit run app.py
```
