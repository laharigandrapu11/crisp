function buildHuffmanTree(text) {
  if (!text || text.length === 0) return HUFFMAN_SAMPLE;

  const freq = {};
  for (const c of text) freq[c] = (freq[c] || 0) + 1;
  const total = text.length;

  let nodes = Object.entries(freq).map(([char, count]) => ({
    name: char === " " ? "␣" : char,
    weight: count / total,
    count,
    isLeaf: true
  }));

  if (nodes.length === 1) {
    return { name: "root", children: [{ ...nodes[0], code: "0" }] };
  }

  let id = 0;
  let queue = nodes.map(n => ({ ...n, id: id++ }));
  queue.sort((a, b) => a.weight - b.weight);

  while (queue.length > 1) {
    const left = queue.shift();
    const right = queue.shift();
    const parent = {
      name: "internal",
      weight: left.weight + right.weight,
      id: id++,
      isLeaf: false,
      children: [left, right]
    };
    queue.push(parent);
    queue.sort((a, b) => a.weight - b.weight);
  }

  function assignCodes(node, code = "") {
    if (node.isLeaf) { node.code = code || "0"; return; }
    if (node.children) {
      assignCodes(node.children[0], code + "0");
      assignCodes(node.children[1], code + "1");
    }
  }
  const root = queue[0];
  assignCodes(root);
  return root;
}

const HUFFMAN_SAMPLE = {
  name: "root",
  children: [
    { name: "a", weight: 0.50, code: "0", isLeaf: true },
    {
      name: "internal",
      children: [
        { name: "n", weight: 0.33, code: "10", isLeaf: true },
        { name: "b", weight: 0.17, code: "11", isLeaf: true }
      ]
    }
  ]
};

function injectCodes(node, codeMap) {
  if (!node) return node;
  const isLeaf = !node.children || node.children.length === 0;
  if (isLeaf && codeMap[node.name] !== undefined) {
    node = { ...node, code: codeMap[node.name] };
  }
  if (node.children) {
    node = { ...node, children: node.children.map(c => injectCodes(c, codeMap)) };
  }
  return node;
}

function HuffmanTree({ treeData, codeMap, swaps, containerWidth }) {
  const svgRef = React.useRef(null);
  const wrapRef = React.useRef(null);
  const tooltipRef = React.useRef(null);
  const [dims, setDims] = React.useState({ w: 560, h: 320 });

  React.useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(entries => {
      const { width } = entries[0].contentRect;
      if (width > 0) setDims(d => ({ ...d, w: width }));
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  React.useEffect(() => {
    const raw = treeData || HUFFMAN_SAMPLE;
    const data = codeMap ? injectCodes(raw, codeMap) : raw;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const margin = { top: 50, right: 20, bottom: 80, left: 20 };
    const W = dims.w - margin.left - margin.right;

    const root = d3.hierarchy(data);
    const depth = root.height;
    const H = Math.max(220, depth * 110) - margin.top - margin.bottom;

    svg
      .attr("width", dims.w)
      .attr("height", H + margin.top + margin.bottom);

    const zoom = d3.zoom().scaleExtent([0.3, 3]).on("zoom", (e) => {
      g.attr("transform", e.transform);
    });
    svg.call(zoom);

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    d3.tree().size([W, H])(root);

    const swappedNums = new Set((swaps || []).flat());

    const BLOCK_PALETTE = [
      "#5ba4cf","#f4a261","#57cc99","#c77dff","#f9c74f",
      "#e76f51","#43aa8b","#a8dadc","#e9c46a","#9b72cf"
    ];
    const uniqueWeights = [...new Set(root.descendants().map(d => d.data.weight))].sort((a,b)=>a-b);
    const weightColor = {};
    uniqueWeights.forEach((w, i) => { weightColor[w] = BLOCK_PALETTE[i % BLOCK_PALETTE.length]; });

    const isLeaf = d => !d.data.children || d.data.children.length === 0;
    const isNYT  = d => d.data.name === "NYT";
    const nodeColor = d => {
      if (isNYT(d))  return "#9aa0a6";
      if (d.data.weight === undefined) return isLeaf(d) ? "rgba(0,200,160,1)" : "#1a3a5c";
      return weightColor[d.data.weight] || "#9aa0a6";
    };

    g.selectAll(".link")
      .data(root.links())
      .enter().append("path")
      .attr("fill", "none")
      .attr("stroke", "#1a3a5c")
      .attr("stroke-width", 1)
      .attr("opacity", 0.35)
      .attr("d", d3.linkVertical().x(d => d.x).y(d => d.y));

    g.selectAll(".edge-label")
      .data(root.links())
      .enter().append("text")
      .attr("x", d => (d.source.x + d.target.x) / 2 + (d.target.x < d.source.x ? -8 : 8))
      .attr("y", d => (d.source.y + d.target.y) / 2)
      .attr("text-anchor", "middle")
      .attr("font-family", "JetBrains Mono, monospace")
      .attr("font-size", 10)
      .attr("font-weight", "600")
      .attr("fill", "rgba(0,180,140,0.95)")
      .text(d => {
        const siblings = d.source.children || [];
        return siblings.indexOf(d.target) === 0 ? "0" : "1";
      });

    const node = g.selectAll(".node")
      .data(root.descendants())
      .enter().append("g")
      .attr("transform", d => `translate(${d.x},${d.y})`);

    node.append("circle")
      .attr("r", d => isLeaf(d) ? 7 : 5)
      .attr("fill", d => nodeColor(d))
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .attr("opacity", d => isNYT(d) ? 0.6 : 1);

    node.filter(d => swappedNums.has(d.data.number))
      .append("circle")
      .attr("r", d => isLeaf(d) ? 12 : 10)
      .attr("fill", "none")
      .attr("stroke", "#ff6b35")
      .attr("stroke-width", 2)
      .attr("opacity", 0.9)
      .append("animate")
        .attr("attributeName", "r")
        .attr("values", d => isLeaf(d) ? "12;16;12" : "10;14;10")
        .attr("dur", "1s")
        .attr("repeatCount", "3");

    node.filter(d => swappedNums.has(d.data.number))
      .append("text")
      .attr("y", -22)
      .attr("text-anchor", "middle")
      .attr("font-family", "JetBrains Mono, monospace")
      .attr("font-size", 8)
      .attr("font-weight", "700")
      .attr("fill", "#ff6b35")
      .text("↔ swap");

    node.filter(d => d.data.number !== undefined)
      .append("text")
      .attr("y", -12)
      .attr("text-anchor", "middle")
      .attr("font-family", "JetBrains Mono, monospace")
      .attr("font-size", 9)
      .attr("fill", "#888")
      .text(d => `#${d.data.number}`);

    node.filter(d => isLeaf(d))
      .append("text")
      .attr("y", 20)
      .attr("text-anchor", "middle")
      .attr("font-family", "JetBrains Mono, monospace")
      .attr("font-size", 11)
      .attr("font-weight", "600")
      .attr("fill", d => isNYT(d) ? "#9aa0a6" : "#14161a")
      .text(d => isNYT(d) ? "NYT" : d.data.name);

    node.filter(d => isLeaf(d))
      .append("text")
      .attr("y", 32)
      .attr("text-anchor", "middle")
      .attr("font-family", "JetBrains Mono, monospace")
      .attr("font-size", 9)
      .attr("fill", "#aaa")
      .text(d => `w=${d.data.weight}`);

    const tooltip = d3.select(tooltipRef.current);
    node.on("mouseover", (event, d) => {
      const lines = isLeaf(d)
        ? [`symbol: "${d.data.name}"`, `weight: ${d.data.weight}`, `node #: ${d.data.number}`, `code: ${d.data.code||"—"}`]
        : [`${d.data.name}`, `weight: ${d.data.weight}`, `node #: ${d.data.number}`];
      tooltip.style("opacity", 1).html(lines.join("<br/>"));
    }).on("mousemove", (event) => {
      const rect = wrapRef.current.getBoundingClientRect();
      tooltip.style("left", `${event.clientX - rect.left + 12}px`).style("top", `${event.clientY - rect.top - 10}px`);
    }).on("mouseleave", () => tooltip.style("opacity", 0));

  }, [treeData, dims]);

  return (
    <div ref={wrapRef} style={{ width: "100%", overflowX: "auto", position: "relative" }}>
      <svg ref={svgRef} style={{ display: "block", cursor: "grab" }} />
      <div ref={tooltipRef} style={{
        position: "absolute", pointerEvents: "none", opacity: 0, transition: "opacity 0.15s",
        background: "#0a1628", color: "#e4e2da", fontFamily: "JetBrains Mono, monospace",
        fontSize: 11, padding: "6px 10px", borderRadius: 4, lineHeight: 1.7,
        border: "1px solid rgba(0,200,160,0.3)", whiteSpace: "nowrap"
      }} />
    </div>
  );
}

Object.assign(window, { HuffmanTree, HUFFMAN_SAMPLE, buildHuffmanTree });
