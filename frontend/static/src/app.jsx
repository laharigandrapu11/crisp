function App(){
  const { values: tweaks, visible: tweaksVisible, update: updateTweaks } = useTweaks();
  const { state, run, reset } = usePipelineRunner();
  const [selected, setSelected] = React.useState(SAMPLES[0]);
  const [uploadedName, setUploadedName] = React.useState(null);
  const [drag, setDrag] = React.useState(false);
  const [history, setHistory] = React.useState([]);
  const [payloadExpanded, setPayloadExpanded] = React.useState(false);
  const [bitsExpanded, setBitsExpanded] = React.useState(false);
  const [extractedExpanded, setExtractedExpanded] = React.useState(false);
  const [recoveredExpanded, setRecoveredExpanded] = React.useState(false);
  const fileRef = React.useRef(null);
  const resultsRef = React.useRef(null);
  const [resultsHighlighted, setResultsHighlighted] = React.useState(false);

  React.useEffect(() => {
    if (state.result){
      setHistory(h => [...h, state.result].slice(-12));
    }
  }, [state.result]);

  const onViewResults = () => {
    if (resultsRef.current) {
      resultsRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    setResultsHighlighted(true);
    setTimeout(() => setResultsHighlighted(false), 2000);
  };

  const onRun = async () => {
    let imageBase64 = selected.imageBase64;
    if (!imageBase64 && selected.src) {
      imageBase64 = await fetchSampleBase64(selected.src);
    }
    run({ ...selected, imageBase64 });
  };
  const onReset = () => { reset(); };

  const svgToBase64 = (svgEl) => new Promise((resolve) => {
    const canvas = document.createElement("canvas");
    canvas.width = 200; canvas.height = 200;
    const ctx = canvas.getContext("2d");
    const svgStr = new XMLSerializer().serializeToString(svgEl);
    const blob = new Blob([svgStr], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, 200, 200);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL("image/png").split(",")[1]);
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(""); };
    img.src = url;
  });

  const onFile = (f) => {
    if (!f) return;
    setUploadedName(f.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const base64 = e.target.result.split(",")[1];
      setSelected({ id: "uploaded", label: f.name, seed: f.name.length + 3, imageBase64: base64 });
    };
    reader.readAsDataURL(f);
  };

  const dropProps = {
    onDragOver: (e) => { e.preventDefault(); setDrag(true); },
    onDragLeave: () => setDrag(false),
    onDrop: (e) => {
      e.preventDefault(); setDrag(false);
      const f = e.dataTransfer.files?.[0];
      onFile(f);
    }
  };

  const statusBanner = (() => {
    if (state.running){
      const label = ["Initializing…","Stage 1 — OCR inference","Stage 2 — Huffman encode","Stage 2 — decode & verify"][state.stage];
      return <div className="status-banner"><span className="live-dot"/> <span>{label}</span></div>;
    }
    if (state.result){
      return <div className="status-banner ok">
        <span style={{ color: state.result.lossless ? "var(--ok)" : "rgba(220,50,50,1)", fontWeight: 600 }}>{state.result.lossless ? "LOSSLESS" : "MISMATCH"}</span>
        <span className="muted">{state.result.lossless ? `Recovered matches original` : `Mismatch — decompress output differs`} · {fmtMs(state.result.totalLatency)} end-to-end</span>
      </div>;
    }
    return <div className="status-banner idle"><span className="muted">Idle — choose a sample or drop an image to begin.</span></div>;
  })();

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead-inner">
          <div className="brand">
            <div className="brand-mark">CRISP<span className="dot">.</span></div>
            <div className="brand-sub">2-Stage Neural Compression Pipeline · v0.1</div>
          </div>
          <div className="masthead-meta">
            <span className="pill"><span className="live-dot"/> services online</span>
          </div>
        </div>
      </header>

      <main className="container">
        <div className="section-h">
          <div>
            <div className="lead">Pipeline Console</div>
          </div>
          <div className="sub"></div>
        </div>

        <div className="cols">
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <section className="panel">
              <div className="panel-head">
                <span className="title">Upload image</span>
                <span className="meta">PNG · JPG</span>
              </div>
              <div className="panel-body">
                <div
                  className={`upload ${drag ? "drag" : ""}`}
                  {...dropProps}
                  onClick={() => fileRef.current?.click()}
                  role="button"
                >
                  <div className="glyph">↑</div>
                  <div className="lead">Drop image, or click to browse</div>
                  <div className="sub">{uploadedName ? `Selected: ${uploadedName}` : ""}</div>
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/png,image/jpeg"
                    style={{ display: "none" }}
                    onChange={(e) => onFile(e.target.files?.[0])}
                  />
                </div>

                <div style={{ marginTop: 18 }}>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-3)", marginBottom: 8 }}>
                    Sample images
                  </div>
                  <div className="sample-row">
                    {SAMPLES.map((s, i) => (
                      <div key={s.id}
                        data-sample-id={s.id}
                        className={`sample-tile ${selected.id === s.id ? "selected" : ""}`}
                        onClick={() => { setSelected(s); setUploadedName(null); }}>
                        <div className="num">{String(i+1).padStart(2,"0")}</div>
                        <img src={s.src} alt={s.label} style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="hairline"/>

                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <button className="btn primary block" onClick={onRun} disabled={state.running}>
                    {state.running ? "Running…" : "Run pipeline"}
                    <span className="kbd">↵</span>
                  </button>
                </div>
                {(state.result || state.running) && (
                  <div style={{ marginTop: 8, textAlign: "center" }}>
                    <button className="reset-link" onClick={onReset} disabled={state.running}>reset run</button>
                  </div>
                )}
              </div>
            </section>

            <section className="panel" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
              <div className="panel-head">
                <span className="title">Preview</span>
                <span className="meta">raw input</span>
              </div>
              <div className="preview">
                {selected.src
                  ? <img src={selected.src} alt={selected.label} style={{ width: "100%", height: "100%", objectFit: "contain", padding: "8px" }} />
                  : selected.imageBase64
                    ? <img src={`data:image/png;base64,${selected.imageBase64}`} alt="uploaded" style={{ width: "100%", height: "100%", objectFit: "contain", padding: "8px" }} />
                    : <NoisyDigit value={selected.label} seed={selected.seed || 1}/>
                }
              </div>
            </section>

            <section className="panel">
              <div className="panel-head">
                <span className="title">Byte comparison</span>
                <span className="meta">{state.result ? `${state.result.origBytes} B → ${state.result.compBytes} B` : "pending"}</span>
              </div>
              <div className="panel-body">
                <BytesBar result={state.result}/>
              </div>
            </section>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {statusBanner}

            <section className="panel">
                <div className="panel-head">
                <span className="title">Key metrics</span>
                <span className="meta"></span>
              </div>
              <HeroMetrics result={state.result} history={history}/>
            </section>

            <section className="panel" style={{ position: "relative", zIndex: 1 }}>
                <div className="panel-head">
                <span className="title">Pipeline</span>
                <span className="meta">{tweaks.pipelineVariant} view</span>
              </div>
              <div className="panel-body" style={{ padding: tweaks.pipelineVariant === "stepper" ? 0 : 0 }}>
                <PipelineView
                  variant={tweaks.pipelineVariant}
                  stage={state.stage}
                  progress={state.progress}
                  result={state.result}
                  sample={selected}
                  onViewResults={onViewResults}
                />
              </div>
            </section>

            <div ref={resultsRef}>
              <section className="panel" style={{
                transition: "box-shadow 0.3s",
                boxShadow: resultsHighlighted ? "0 0 0 2px rgba(0,200,160,0.8), 0 0 24px rgba(0,200,160,0.25)" : "none"
              }}>
                    <div className="panel-head">
                  <span className="title">Results</span>
                  <span className="meta">{state.result ? <>ready &nbsp;<span style={{ color: state.result.lossless ? "var(--ok)" : "rgba(220,50,50,1)", fontWeight: 600, fontSize: 10 }}>{state.result.lossless ? "\u2713 lossless" : "\u2717 mismatch"}</span></> : "pending"}</span>
                </div>
                <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <div className="result-grid">
                    <div className="k">Extracted text</div>
                    <div className="v">
                      {state.result
                        ? <span className="ocr-out">
                            {extractedExpanded ? state.result.recognized : state.result.recognized.slice(0, 120)}
                            {!extractedExpanded && state.result.recognized.length > 120
                              ? <>{" "}<span onClick={() => setExtractedExpanded(true)} style={{ color: "var(--ink-3)", cursor: "pointer", fontSize: 10, letterSpacing: "0.08em", textDecoration: "underline", textUnderlineOffset: 3, whiteSpace: "nowrap" }}>read more</span></>
                              : extractedExpanded ? <>{" "}<span onClick={() => setExtractedExpanded(false)} style={{ color: "var(--ink-4)", cursor: "pointer", fontSize: 10, letterSpacing: "0.08em", textDecoration: "underline", textUnderlineOffset: 3, whiteSpace: "nowrap" }}>show less</span></> : ""}
                          </span>
                        : <span className="muted" style={{ fontFamily: "var(--mono)" }}>awaiting stage 1…</span>}
                    </div>

                    <div className="k">Compressed<br/>Payload</div>
                    <div className="v">
                      <div className="mono-block" style={{ maxHeight: payloadExpanded ? 320 : 100, overflowY: payloadExpanded ? "auto" : "hidden", transition: "max-height 0.2s" }}>
                        {state.result
                          ? <>{payloadExpanded ? state.result.payload : state.result.payload.slice(0, 140)}{!payloadExpanded && state.result.payload.length > 140
                              ? <span onClick={() => setPayloadExpanded(true)} style={{ color: "var(--ok)", cursor: "pointer", fontWeight: 600 }}>{` …+${state.result.payload.length - 140} chars`}</span>
                              : payloadExpanded ? <span onClick={() => setPayloadExpanded(false)} style={{ color: "var(--ink-4)", cursor: "pointer", display: "block", marginTop: 6 }}>▲ collapse</span> : ""}</>
                          : <span className="muted">—</span>
                        }
                      </div>
                      {state.result && (() => {
                        const allBits = Array.from(atob(state.result.payload))
                          .map(c => c.charCodeAt(0).toString(2).padStart(8, "0"))
                          .join("");
                        const padLen = parseInt(allBits.slice(0, 3), 2);
                        const dataBits = allBits.slice(3);
                        const realBits = padLen > 0 ? dataBits.slice(0, -padLen) : dataBits;
                        const padBits  = padLen > 0 ? dataBits.slice(-padLen) : "";
                        const realGroups = realBits.match(/.{1,8}/g) || [];
                        const visibleGroups = bitsExpanded ? realGroups : realGroups.slice(0, 16);
                        return (
                          <div style={{ marginTop: 8 }}>
                            <div style={{ fontFamily: "var(--mono)", fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--ink-3)", marginBottom: 4 }}>
                              bit string · {realBits.length} data bits + {padLen} padding
                            </div>
                            <div style={{ fontFamily: "var(--mono)", fontSize: 11, lineHeight: 1.8, wordBreak: "break-all" }}>
                              {visibleGroups.map((g, i) => (
                                <span key={i}>
                                  <span style={{ color: i % 2 === 0 ? "var(--ink)" : "var(--ink-3)" }}>{g}</span>
                                  {" "}
                                </span>
                              ))}
                              {!bitsExpanded && realGroups.length > 16 && (
                                <span onClick={() => setBitsExpanded(true)} style={{ color: "var(--ok)", cursor: "pointer", fontWeight: 600 }}>
                                  {" +"}{ realGroups.length - 16} more bytes
                                </span>
                              )}
                              {bitsExpanded && padBits && <span style={{ color: "rgba(180,140,100,0.6)", letterSpacing: "0.05em" }} title="padding bits">{padBits}</span>}
                              {bitsExpanded && (
                                <span onClick={() => setBitsExpanded(false)} style={{ color: "var(--ink-4)", cursor: "pointer", display: "block", marginTop: 6 }}>collapse</span>
                              )}
                            </div>
                          </div>
                        );
                      })()}
                    </div>

                    <div className="k">Recovered</div>
                    <div className="v">
                      {state.result
                        ? <span className="ocr-out">
                            {recoveredExpanded ? state.result.recovered : state.result.recovered.slice(0, 120)}
                            {!recoveredExpanded && state.result.recovered.length > 120
                              ? <>{" "}<span onClick={() => setRecoveredExpanded(true)} style={{ color: "var(--ink-3)", cursor: "pointer", fontSize: 10, letterSpacing: "0.08em", textDecoration: "underline", textUnderlineOffset: 3, whiteSpace: "nowrap" }}>read more</span></>
                              : recoveredExpanded ? <>{" "}<span onClick={() => setRecoveredExpanded(false)} style={{ color: "var(--ink-4)", cursor: "pointer", fontSize: 10, letterSpacing: "0.08em", textDecoration: "underline", textUnderlineOffset: 3, whiteSpace: "nowrap" }}>show less</span></> : ""}
                          </span>
                        : <span className="muted" style={{ fontFamily: "var(--mono)" }}>awaiting stage 3…</span>}
                    </div>
                  </div>

                </div>
              </section>
            </div>
          </div>
        </div>

        <div className="foot">
          <div>CRISP · neural compression</div>
          <div>tf.keras · adaptive huffman · vitter algorithm v</div>
        </div>
      </main>

      <TweaksPanel values={tweaks} visible={tweaksVisible} update={updateTweaks} />

    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
