function computeEntropy(text){
  if (!text) return 0;
  const counts = {};
  for (const c of text) counts[c] = (counts[c] || 0) + 1;
  const n = text.length;
  let H = 0;
  for (const k in counts){
    const p = counts[k] / n;
    H += -p * Math.log2(p);
  }
  return H;
}


function usePipelineRunner(){
  const [state, setState] = React.useState({
    running: false,
    stage: 0,
    progress: [0,0,0],
    result: null,
    error: null,
    log: []
  });

  const run = async (sample) => {
    const log = [];
    const addLog = (msg) => {
      const t = new Date().toISOString().split("T")[1].replace("Z","");
      log.push(`[${t}] ${msg}`);
    };

    setState(s => ({ ...s, running: true, stage: 1, progress: [0,0,0], result: null, error: null, log: [] }));

    try {
      addLog(`POST /api/ocr  size=${sample.imageBase64.length} chars`);
      const t0 = performance.now();
      setState(s => ({ ...s, progress: [0.4, 0, 0] }));
      const ocrRes = await fetch("/api/ocr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: sample.imageBase64 })
      });
      if (!ocrRes.ok) throw new Error(`OCR failed: ${ocrRes.status}`);
      const ocrData = await ocrRes.json();
      const ocrLatency = (performance.now() - t0) / 1000;
      const recognized = ocrData.extracted_text;
      const denoisedImage = ocrData.denoised_image || null;
      const characterData = ocrData.character_data || [];
      addLog(`stage1.response: text="${recognized}" (${(ocrLatency*1000).toFixed(1)}ms)`);
      setState(s => ({ ...s, stage: 2, progress: [1, 0, 0] }));

      addLog(`POST /api/compress  text="${recognized}"`);
      const t1 = performance.now();
      setState(s => ({ ...s, progress: [1, 0.5, 0] }));
      const compRes = await fetch("/api/compress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: recognized })
      });
      if (!compRes.ok) throw new Error(`Compress failed: ${compRes.status}`);
      const compData = await compRes.json();
      const compLatency = (performance.now() - t1) / 1000;
      const m = compData.metrics || {};
      const metrics = {
        origBytes:  m.original_bytes   ?? recognized.length,
        compBytes:  m.compressed_bytes ?? recognized.length,
        origBits:   (m.original_bytes  ?? recognized.length) * 8,
        compBits:   (m.compressed_bytes ?? recognized.length) * 8,
        ratio:      m.compression_ratio    ?? 1.0,
        entropy:    m.entropy              ?? computeEntropy(recognized),
        avgBits:    m.avg_bits_per_symbol  ?? 8.0,
        efficiency: m.encoding_efficiency ?? 1.0,
        payload:    compData.payload_base64 ?? "",
      };
      const treeStructure = compData.tree_structure || null;
      const codeMap = compData.code_map || {};
      addLog(`stage2.compress: in=${metrics.origBytes}B out=${metrics.compBytes}B ratio=${metrics.ratio.toFixed(2)}x`);
      setState(s => ({ ...s, stage: 3, progress: [1, 1, 0] }));

      addLog(`POST /api/decompress`);
      const t2 = performance.now();
      setState(s => ({ ...s, progress: [1, 1, 0.5] }));
      const decRes = await fetch("/api/decompress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payload_base64: metrics.payload })
      });
      if (!decRes.ok) throw new Error(`Decompress failed: ${decRes.status}`);
      const decData = await decRes.json();
      const decLatency = (performance.now() - t2) / 1000;
      const recovered = decData.text;
      const lossless = recovered === recognized;
      addLog(`stage2.decompress: out="${recovered}" lossless=${lossless}`);

      const totalLatency = ocrLatency + compLatency + decLatency;
      setState({
        running: false, stage: 4, progress: [1,1,1],
        result: { recognized, recovered, lossless, ...metrics, ocrLatency, compLatency, decLatency, totalLatency, denoisedImage, characterData, treeStructure, codeMap },
        error: null, log
      });

    } catch(err) {
      addLog(`ERROR: ${err.message}`);
      setState(s => ({ ...s, running: false, stage: 0, error: err.message, log }));
    }
  };

  const reset = () => {
    setState({ running: false, stage: 0, progress: [0,0,0], result: null, error: null, log: [] });
  };

  return { state, run, reset };
}

function animateProgress(duration, onTick){
  return new Promise((resolve) => {
    const start = performance.now();
    const step = (now) => {
      const p = Math.min(1, (now - start) / duration);
      onTick(p);
      if (p < 1) requestAnimationFrame(step);
      else resolve();
    };
    requestAnimationFrame(step);
  });
}

Object.assign(window, { usePipelineRunner, computeEntropy });
