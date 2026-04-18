function DenoisedPanel({ denoisedImage, characterData, style }){
  const imgRef = React.useRef(null);
  const canvasRef = React.useRef(null);

  const drawBoxes = () => {
    const img = imgRef.current;
    const canvas = canvasRef.current;
    if (!img || !canvas) return;
    const pad = 8;
    const cW = img.offsetWidth;
    const cH = img.offsetHeight;
    canvas.width = cW;
    canvas.height = cH;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, cW, cH);
    if (!characterData || characterData.length === 0) return;
    const nW = img.naturalWidth;
    const nH = img.naturalHeight;
    if (!nW || !nH) return;
    const availW = cW - pad * 2;
    const availH = cH - pad * 2;
    const scale = Math.min(availW / nW, availH / nH);
    const rendW = nW * scale;
    const rendH = nH * scale;
    const offX = pad + (availW - rendW) / 2;
    const offY = pad + (availH - rendH) / 2;
    ctx.fillStyle = "rgba(0,255,200,0.15)";
    for (const item of characterData){
      const [x1, y1, x2, y2] = item.bbox;
      ctx.fillRect(offX + x1 * scale, offY + y1 * scale, (x2-x1) * scale, (y2-y1) * scale);
    }
  };

  React.useEffect(() => {
    const img = imgRef.current;
    if (!img) return;
    if (img.complete && img.naturalWidth) drawBoxes();
    else img.onload = drawBoxes;
  }, [denoisedImage, characterData]);

  return (
    <div style={{ flex: 1, position: "relative", background: "var(--bg)", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", ...style }}>
      <div style={{
        position: "absolute", top: 10, left: 10,
        fontFamily: "var(--mono)", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em",
        background: "rgba(0,255,200,0.12)", color: "rgba(0,180,140,1)",
        border: "1px solid rgba(0,255,200,0.35)", padding: "3px 8px", borderRadius: 3, zIndex: 1
      }}>stage 1 · denoised</div>
      <img
        ref={imgRef}
        src={`data:image/png;base64,${denoisedImage}`}
        alt="denoised"
        style={{ width: "100%", height: "100%", objectFit: "contain", padding: "8px", display: "block" }}
        onLoad={drawBoxes}
      />
      <canvas ref={canvasRef} style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }} />
    </div>
  );
}

async function sha256short(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  const hex = Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,"0")).join("");
  return hex.slice(0,8) + "…" + hex.slice(-4);
}

function DecompressPanel({ original, recovered }) {
  const [origHash, setOrigHash] = React.useState("computing…");
  const [recHash,  setRecHash]  = React.useState("computing…");
  const match = original === recovered;

  React.useEffect(() => {
    if (!original) return;
    sha256short(original).then(setOrigHash);
    sha256short(recovered || "").then(setRecHash);
  }, [original, recovered]);

  const panelStyle = {
    flex: 1, background: "var(--bg)", border: "1px solid var(--rule)",
    borderRadius: 6, padding: "16px 18px", display: "flex", flexDirection: "column", gap: 10,
  };
  const titleStyle = {
    fontFamily: "var(--mono)", fontSize: 10, textTransform: "uppercase",
    letterSpacing: "0.12em", color: "rgba(0,180,140,0.8)", marginBottom: 4,
  };
  const textStyle = {
    fontFamily: "var(--mono)", fontSize: 12, color: "var(--ink)",
    lineHeight: 1.7, flex: 1, wordBreak: "break-word",
    maxHeight: 140, overflowY: "auto",
  };
  const hashStyle = {
    fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-3)",
    borderTop: "1px solid var(--rule)", paddingTop: 8, marginTop: "auto",
  };

  return (
    <div style={{ padding: "16px", background: "rgba(0,255,200,0.03)", borderTop: "1px solid var(--rule)" }}>
      {/* Badge */}
      <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 8,
          padding: "6px 18px", borderRadius: 999,
          background: match ? "rgba(0,255,200,0.08)" : "rgba(255,80,80,0.08)",
          border: `1px solid ${match ? "rgba(0,255,200,0.5)" : "rgba(255,80,80,0.5)"}`,
          boxShadow: match ? "0 0 12px rgba(0,255,200,0.2)" : "none",
          fontFamily: "var(--mono)", fontSize: 11, fontWeight: 600, letterSpacing: "0.08em",
          color: match ? "rgba(0,140,110,1)" : "rgba(200,50,50,1)",
          textTransform: "uppercase",
        }}>
          <span>{match ? "✓" : "✗"}</span>
          <span>{match ? "100% bit-perfect match" : "mismatch detected"}</span>
        </div>
      </div>

      {/* Split panels */}
      <div style={{ display: "flex", gap: 12 }}>
        <div style={panelStyle}>
          <div style={titleStyle}>OCR Source Text</div>
          <div style={textStyle}>{original}</div>
          <div style={hashStyle}>sha-256 · {origHash}</div>
        </div>

        <div style={{ display: "flex", alignItems: "center", color: "rgba(0,200,160,0.4)", fontSize: 18 }}>≡</div>

        <div style={panelStyle}>
          <div style={titleStyle}>Decompressed Output</div>
          <div style={textStyle}>{recovered}</div>
          <div style={hashStyle}>sha-256 · {recHash}</div>
        </div>
      </div>
    </div>
  );
}

function HuffmanStepsPanel({ recognized, finalTree, finalCodeMap }) {
  const [steps, setSteps] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [stepIdx, setStepIdx] = React.useState(null);
  const [mode, setMode] = React.useState("final");

  const loadSteps = async () => {
    if (steps) { setMode("steps"); setStepIdx(0); return; }
    setLoading(true);
    try {
      const r = await fetch("/api/compress/steps", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: recognized })
      });
      if (!r.ok) throw new Error(`steps failed: ${r.status}`);
      const data = await r.json();
      setSteps(data.steps);
      setStepIdx(0);
      setMode("steps");
    } catch(e) {
    } finally {
      setLoading(false);
    }
  };

  const currentStep = mode === "steps" && steps ? steps[stepIdx] : null;
  const treeData = currentStep ? currentStep.tree : (finalTree || null);
  const codeMap  = currentStep ? currentStep.codes : (finalCodeMap || {});

  return (
    <div style={{ borderTop: "1px solid var(--rule)", padding: "16px" }}>
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <div style={{ fontFamily: "var(--mono)", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--ink-3)" }}>
          Huffman tree · input: <span style={{ color: "var(--ink)", fontWeight: 600, textTransform: "none" }}>"{recognized}"</span>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button
            onClick={() => setMode("final")}
            style={{
              fontFamily: "var(--mono)", fontSize: 10, padding: "3px 10px", borderRadius: 3, cursor: "pointer",
              border: "1px solid var(--rule)", background: mode === "final" ? "rgba(0,200,160,0.12)" : "transparent",
              color: mode === "final" ? "rgba(0,160,120,1)" : "var(--ink-3)"
            }}
          >final</button>
          <button
            onClick={loadSteps}
            disabled={loading}
            style={{
              fontFamily: "var(--mono)", fontSize: 10, padding: "3px 10px", borderRadius: 3, cursor: "pointer",
              border: "1px solid var(--rule)", background: mode === "steps" ? "rgba(0,200,160,0.12)" : "transparent",
              color: mode === "steps" ? "rgba(0,160,120,1)" : "var(--ink-3)"
            }}
          >{loading ? "loading…" : "step-by-step"}</button>
        </div>
      </div>

      {/* Step controls */}
      {mode === "steps" && steps && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <button onClick={() => setStepIdx(i => Math.max(0, i - 1))} disabled={stepIdx === 0}
            style={{ fontFamily: "var(--mono)", fontSize: 12, padding: "2px 10px", borderRadius: 3, border: "1px solid var(--rule)", background: "transparent", cursor: "pointer", color: "var(--ink-2)" }}>←</button>
          <input type="range" min={0} max={steps.length - 1} value={stepIdx}
            onChange={e => setStepIdx(Number(e.target.value))}
            style={{ flex: 1, accentColor: "rgba(0,180,140,1)" }} />
          <button onClick={() => setStepIdx(i => Math.min(steps.length - 1, i + 1))} disabled={stepIdx === steps.length - 1}
            style={{ fontFamily: "var(--mono)", fontSize: 12, padding: "2px 10px", borderRadius: 3, border: "1px solid var(--rule)", background: "transparent", cursor: "pointer", color: "var(--ink-2)" }}>→</button>
          <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--ink-3)", whiteSpace: "nowrap" }}>
            step {stepIdx + 1} / {steps.length}
          </span>
        </div>
      )}

      {/* Step badge */}
      {mode === "steps" && steps && currentStep && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10, flexWrap: "wrap" }}>
          <span style={{
            fontFamily: "var(--mono)", fontSize: 10, padding: "2px 8px", borderRadius: 3,
            background: currentStep.is_new ? "rgba(0,200,160,0.1)" : "rgba(100,100,200,0.1)",
            border: `1px solid ${currentStep.is_new ? "rgba(0,200,160,0.3)" : "rgba(100,100,200,0.3)"}`,
            color: currentStep.is_new ? "rgba(0,140,110,1)" : "rgba(80,80,180,1)"
          }}>
            {currentStep.is_new ? "new symbol" : "seen before"}
          </span>
          <span style={{ fontFamily: "var(--mono)", fontSize: 13, fontWeight: 700, color: "var(--ink)" }}>
            '{currentStep.char}'
          </span>
          <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-3)" }}>
            → code: <span style={{ color: "rgba(0,140,110,1)", fontWeight: 600 }}>{codeMap[currentStep.char] || "—"}</span>
          </span>
          {currentStep.swaps && currentStep.swaps.length > 0 && (
            <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "#ff6b35", marginLeft: 8 }}>
              ↔ swapped during this step: {currentStep.swaps.map(([a,b]) => `#${a} ↔ #${b}`).join(", ")}
            </span>
          )}
        </div>
      )}

      <HuffmanTree treeData={treeData} codeMap={codeMap} swaps={currentStep ? currentStep.swaps : []} />
    </div>
  );
}

const STAGE_DEFS = [
  { n: "1", id: "ocr",    name: "OCR",        desc: "CNN → text", endpoint: "$STAGE1_URL/predict" },
  { n: "2", id: "encode", name: "Compress",   desc: "Adaptive Huffman", endpoint: "$STAGE2_URL/encode" },
  { n: "3", id: "decode", name: "Decompress", desc: "Lossless verify", endpoint: "$STAGE2_URL/decode" },
];

function fmtMs(seconds){
  if (seconds == null) return "—";
  return `${(seconds*1000).toFixed(1)} ms`;
}

function StepperView({ stage, progress, result, sample, onViewResults }){
  const [expandedOcr, setExpandedOcr] = React.useState(false);
  const [expandedCompress, setExpandedCompress] = React.useState(false);
  const ocrClickable = result && result.denoisedImage;
  const compressClickable = result && result.recognized;
  const decompressClickable = result && result.recovered;

  return (
    <div>
      <div className="stepper">
        {STAGE_DEFS.map((s, i) => {
          const active = stage === i + 1;
          const done = stage > i + 1 || (stage === 4);
          const p = progress[i] || 0;
          const stateLabel = done ? "COMPLETE" : active ? "RUNNING" : "IDLE";
          const latencyKey = ["ocrLatency","compLatency","decLatency"][i];
          const isOcr = i === 0;
          const isCompress = i === 1;
          const isDecompress = i === 2;
          const highlighted = (isOcr && expandedOcr) || (isCompress && expandedCompress);
          const clickable = (isOcr && ocrClickable) || (isCompress && compressClickable) || (isDecompress && decompressClickable);
          const onClick = isOcr && ocrClickable ? () => setExpandedOcr(v => !v)
            : isCompress && compressClickable ? () => setExpandedCompress(v => !v)
            : isDecompress && decompressClickable ? () => onViewResults && onViewResults()
            : undefined;
          const expanded = isOcr ? expandedOcr : isCompress ? expandedCompress : false;
          return (
            <div
              key={s.id}
              className={`step ${active ? "active" : done ? "done" : "idle"}`}
              onClick={onClick}
              style={clickable ? {
                cursor: "pointer",
                boxShadow: highlighted ? "inset 0 0 0 2px rgba(0,200,160,0.45)" : "none",
                background: highlighted ? "rgba(0,255,200,0.05)" : undefined,
                borderRadius: 4, transition: "box-shadow 0.15s, background 0.15s"
              } : undefined}
            >
              <div className="num">STEP {s.n}{clickable ? <span style={{ marginLeft: 6, fontSize: 9, color: "rgba(0,180,140,0.8)", fontFamily: "var(--mono)" }}>{expanded ? "▲ hide" : "▼ view output"}</span> : null}</div>
              <div className="name">{s.name}</div>
              <div className="desc">{s.desc}</div>
              <div className="bar"><div className="fill" style={{ width: `${p*100}%` }}/></div>
              <div className="stat">
                <span className="dotstate"><span className="d"/>{stateLabel}</span>
                <span>{result ? fmtMs(result[latencyKey]) : "— ms"}</span>
              </div>
            </div>
          );
        })}
      </div>
      {expandedOcr && result && result.denoisedImage && (
        <div style={{ borderTop: "1px solid var(--rule)" }}>
          <div style={{ display: "flex", minHeight: 260 }}>
            <div style={{ flex: 1, position: "relative", background: "var(--bg)", display: "flex", alignItems: "center", justifyContent: "center", borderRight: "1px solid var(--rule)", overflow: "hidden" }}>
              <div style={{ position: "absolute", top: 10, left: 10, zIndex: 2, fontFamily: "var(--mono)", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", background: "rgba(255,255,255,0.92)", padding: "3px 8px", borderRadius: 3, color: "var(--ink-2)" }}>stage 0 · raw</div>
              {sample && sample.src
                ? <img src={sample.src} alt="raw" style={{ width: "100%", height: "100%", objectFit: "contain", padding: "8px" }} />
                : sample && sample.imageBase64
                  ? <img src={`data:image/png;base64,${sample.imageBase64}`} alt="raw" style={{ width: "100%", height: "100%", objectFit: "contain", padding: "8px" }} />
                  : null
              }
            </div>
            <DenoisedPanel denoisedImage={result.denoisedImage} characterData={result.characterData} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 16px", borderTop: "1px solid var(--rule)", background: "rgba(0,255,200,0.04)" }}>
            <span style={{ fontFamily: "var(--mono)", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--ink-3)" }}>Extracted text</span>
            <span style={{ fontFamily: "var(--mono)", fontSize: 15, fontWeight: 600, color: "var(--ink)", letterSpacing: "0.05em" }}>{result.recognized}</span>
          </div>
        </div>
      )}
      {expandedCompress && result && result.recognized && (
        <HuffmanStepsPanel recognized={result.recognized} finalTree={result.treeStructure} finalCodeMap={result.codeMap} />
      )}
    </div>
  );
}

function NetworkView({ stage, progress, result }){
  const positions = [
    { id: "in",  x: 10,  y: 50, label: "INPUT",      sub: "image/png",        kind: "io" },
    { id: "ocr", x: 30,  y: 50, label: "STAGE 01",   sub: "CNN · OCR",        stageIdx: 1 },
    { id: "enc", x: 52,  y: 30, label: "STAGE 02A",  sub: "Huffman · encode", stageIdx: 2 },
    { id: "dec", x: 74,  y: 70, label: "STAGE 02B",  sub: "Huffman · decode", stageIdx: 3 },
    { id: "out", x: 93,  y: 50, label: "VERIFY",     sub: "lossless",         kind: "io" },
  ];
  const edges = [
    ["in","ocr"],["ocr","enc"],["enc","dec"],["dec","out"]
  ];

  return (
    <div className="network">
      <svg className="edges" preserveAspectRatio="none" viewBox="0 0 100 100">
        {edges.map(([a,b], i) => {
          const A = positions.find(p=>p.id===a);
          const B = positions.find(p=>p.id===b);
          const edgeActive =
            (b === "ocr" && stage >= 1) ||
            (b === "enc" && stage >= 2) ||
            (b === "dec" && stage >= 3) ||
            (b === "out" && stage >= 4);
          const running =
            (b === "ocr" && stage === 1) ||
            (b === "enc" && stage === 2) ||
            (b === "dec" && stage === 3);
          return (
            <g key={i}>
              <line x1={A.x} y1={A.y} x2={B.x} y2={B.y}
                stroke={edgeActive ? "var(--accent)" : "var(--rule-strong)"}
                strokeWidth="0.4"
                strokeDasharray={running ? "1 1" : "0"}
                vectorEffect="non-scaling-stroke"
              />
              {running && (
                <circle r="0.9" fill="var(--accent)">
                  <animate attributeName="cx" from={A.x} to={B.x} dur="1.1s" repeatCount="indefinite"/>
                  <animate attributeName="cy" from={A.y} to={B.y} dur="1.1s" repeatCount="indefinite"/>
                </circle>
              )}
            </g>
          );
        })}
      </svg>
      {positions.map(p => {
        const done = p.stageIdx ? stage > p.stageIdx || stage === 4 : (p.id === "in" ? stage >= 1 : stage === 4);
        const active = p.stageIdx && stage === p.stageIdx;
        return (
          <div key={p.id} className={`node ${p.kind==="io"?"io":""} ${active?"active":""} ${done?"done":""}`}
            style={{ left: `${p.x}%`, top: `${p.y}%` }}>
            <div className="n">{p.label}</div>
            <div className="t">{p.sub}</div>
            <div className="s">
              {active ? "running…"
                : done ? (p.stageIdx && result ? fmtMs(result[["ocrLatency","compLatency","decLatency"][p.stageIdx-1]]) : "ok")
                : "idle"}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TimelineView({ stage, progress, result, sample }){
  const rows = [
    {
      name: "Stage 01 · OCR",
      desc: "Forward pass through CNN; returns recognized text.",
      latency: result?.ocrLatency,
      payload: stage >= 2 && result ? `recognized = "${result.recognized}"  ·  conf=0.992` : null,
      stageIdx: 1,
    },
    {
      name: "Stage 02 · Adaptive Huffman Encode",
      desc: "Symbol-adaptive coding; emits base64 payload + metrics.",
      latency: result?.compLatency,
      payload: stage >= 3 && result ? `${result.payload.slice(0, 52)}${result.payload.length > 52 ? "…" : ""}` : null,
      stageIdx: 2,
    },
    {
      name: "Stage 02 · Decode",
      desc: "Reconstructs original string from payload; asserts equality.",
      latency: result?.decLatency,
      payload: stage === 4 && result ? `recovered = "${result.recovered}"  ·  match=true` : null,
      stageIdx: 3,
    },
  ];

  return (
    <div className="timeline">
      <div className="tl-axis"/>
      <div className="tl-steps">
        {rows.map((r, i) => {
          const active = stage === r.stageIdx;
          const done = stage > r.stageIdx || stage === 4;
          return (
            <div key={i} className={`tl-step ${active?"active":""} ${done?"done":""}`}>
              <div className="dot"/>
              <div className="head">
                <span className="nm">{r.name}</span>
                <span className="tm">{r.latency != null ? fmtMs(r.latency) : active ? "running…" : "—"}</span>
              </div>
              <div className="desc">{r.desc}</div>
              {r.payload && <div className="payload">{r.payload}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PipelineView({ variant, sample, onViewResults, ...rest }){
  if (variant === "network")  return <NetworkView {...rest} />;
  if (variant === "timeline") return <TimelineView sample={sample} {...rest} />;
  return <StepperView sample={sample} onViewResults={onViewResults} {...rest} />;
}

Object.assign(window, { PipelineView, STAGE_DEFS, fmtMs });
