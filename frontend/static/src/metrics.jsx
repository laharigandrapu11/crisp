function Sparkline({ points, color = "var(--ink)" }){
  const w = 100, h = 22;
  if (!points || points.length === 0){
    return (
      <svg viewBox={`0 0 ${w} ${h}`} className="spark">
        <line x1="0" y1={h/2} x2={w} y2={h/2} stroke="var(--rule-strong)" strokeWidth="1" strokeDasharray="2 2"/>
      </svg>
    );
  }
  const step = w / (points.length - 1 || 1);
  const d = points.map((p, i) => `${i===0?"M":"L"}${i*step},${h - p*(h-2) - 1}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="spark">
      <path d={d} stroke={color} strokeWidth="1.2" fill="none" vectorEffect="non-scaling-stroke"/>
      <circle cx={(points.length-1)*step} cy={h - points[points.length-1]*(h-2) - 1} r="1.5" fill={color}/>
    </svg>
  );
}

function HeroMetrics({ result }){
  const cells = [
    {
      lbl: "Compression Ratio", val: result ? `${result.ratio.toFixed(2)}×` : "—",
      delta: result ? `−${(100 - 100/result.ratio).toFixed(0)}% bytes` : "",
      deltaClass: "neg"
    },
    {
      lbl: "Entropy", val: result ? result.entropy.toFixed(2) : "—",
      unit: "bits/sym"
    },
    {
      lbl: "Encoding Efficiency", val: result ? `${(result.efficiency*100).toFixed(1)}` : "—",
      unit: "%"
    },
    {
      lbl: "Total Latency", val: result ? `${(result.totalLatency*1000).toFixed(0)}` : "—",
      unit: "ms"
    },
  ];

  return (
    <div className="hero-metrics">
      {cells.map((c, i) => (
        <div className="metric" key={i}>
          <div className="lbl">{c.lbl}</div>
          <div className="val">
            {c.val}
            {c.unit && <span className="unit">{c.unit}</span>}
          </div>
          {c.delta
            ? <div className={`delta ${c.deltaClass||""}`}>{c.delta}</div>
            : <div className="delta muted">&nbsp;</div>
          }
        </div>
      ))}
    </div>
  );
}

function DetailTable({ result }){
  const rows = [
    { k: "Original size",         v: result ? `${result.origBytes} B`   : "—", lane: "var(--ink-3)" },
    { k: "Compressed size",       v: result ? `${result.compBytes} B`   : "—", lane: "var(--accent)" },
    { k: "Avg bits per symbol",   v: result ? result.avgBits.toFixed(3) : "—" },
    { k: "Shannon entropy",       v: result ? result.entropy.toFixed(3) + " bits/sym" : "—" },
    { k: "Efficiency (H/ℓ̄)",     v: result ? (result.efficiency*100).toFixed(2) + " %" : "—" },
    { k: "Stage 1 OCR latency",        v: result ? fmtMs(result.ocrLatency)  : "—" },
    { k: "Stage 2 compress latency",   v: result ? fmtMs(result.compLatency) : "—" },
    { k: "Stage 2 decompress latency", v: result ? fmtMs(result.decLatency)  : "—" },
    { k: "Total end-to-end",           v: result ? fmtMs(result.totalLatency): "—", emph: true },
  ];
  return (
    <table className="detail-table">
      <thead>
        <tr><th>Metric</th><th className="num">Value</th></tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td>
              {r.lane && <span className="lane" style={{ background: r.lane }}/>}
              {r.k}
            </td>
            <td className="num" style={r.emph ? { fontWeight: 600, color: "var(--ink)" } : null}>{r.v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function BytesBar({ result }){
  if (!result){
    return <div className="muted" style={{ fontFamily: "var(--mono)", fontSize: 12 }}>Run pipeline to compare byte lengths.</div>;
  }
  const maxB = Math.max(result.origBytes, result.compBytes);
  const origPct = (result.origBytes / maxB) * 100;
  const compPct = (result.compBytes / maxB) * 100;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="bytes">
        <div className="lane-lbl">Original</div>
        <div className="bar-track"><div className="bar-fill bar-stripe" style={{ width: `${origPct}%` }}/></div>
        <div className="lane-val">{result.origBytes} B</div>
      </div>
      <div className="bytes">
        <div className="lane-lbl">Compressed</div>
        <div className="bar-track"><div className="bar-fill bar-stripe accent" style={{ width: `${compPct}%` }}/></div>
        <div className="lane-val">{result.compBytes} B</div>
      </div>
    </div>
  );
}

Object.assign(window, { HeroMetrics, DetailTable, BytesBar, Sparkline });
