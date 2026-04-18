const DigitStrokes = {
  "0": "M28 14 C14 14, 10 30, 10 50 C10 72, 16 86, 30 86 C44 86, 50 72, 50 50 C50 30, 44 14, 30 14 Z",
  "1": "M18 26 L30 18 L30 84 M18 84 L44 84",
  "2": "M14 28 C14 18, 24 14, 32 14 C42 14, 50 22, 50 32 C50 42, 42 50, 32 56 C22 62, 12 72, 12 84 L52 84",
  "3": "M14 22 C20 14, 32 12, 40 18 C48 24, 48 36, 38 42 C30 46, 24 46, 24 46 C34 48, 50 52, 50 68 C50 82, 36 88, 26 86 C16 84, 12 76, 12 72",
  "4": "M40 14 L12 60 L52 60 M42 30 L42 86",
  "5": "M48 16 L18 16 L14 48 C22 40, 38 40, 46 50 C54 62, 48 80, 36 84 C24 88, 14 82, 12 74",
  "6": "M44 20 C34 12, 18 14, 14 34 C10 56, 14 78, 28 84 C42 90, 52 76, 50 62 C48 50, 36 44, 24 48 C18 50, 14 56, 14 56",
  "7": "M12 18 L52 18 L28 86",
  "8": "M30 14 C18 14, 14 24, 16 32 C18 40, 26 44, 32 46 C40 48, 50 54, 50 66 C50 80, 38 88, 28 86 C18 84, 10 76, 12 66 C14 58, 22 50, 30 46 C22 44, 16 38, 16 28 C16 20, 22 14, 30 14 Z",
  "9": "M46 40 C46 26, 36 14, 26 16 C16 18, 10 30, 14 42 C18 52, 32 52, 40 44 C44 40, 46 34, 46 34 L46 86"
};

function NoisyDigit({ value, seed=1, showNoise=true, w=200, h=200 }){
  const chars = String(value).split("");
  const pad = 8;
  const charW = (w - pad*2) / Math.max(chars.length, 1);

  const rnd = (i) => {
    const x = Math.sin((seed + i) * 9999.13) * 10000;
    return x - Math.floor(x);
  };

  const noise = [];
  if (showNoise){
    for (let i = 0; i < 180; i++){
      noise.push({
        x: rnd(i) * w,
        y: rnd(i + 400) * h,
        r: rnd(i + 800) * 1.6 + 0.2,
        o: rnd(i + 1200) * 0.5 + 0.1
      });
    }
  }

  return (
    <svg viewBox={`0 0 ${w} ${h}`} xmlns="http://www.w3.org/2000/svg" role="img" aria-label={`handwritten ${value}`}>
      <rect x="0" y="0" width={w} height={h} fill="#0c0d10" />
      {/* scan lines */}
      <g opacity="0.12">
        {Array.from({length: 24}).map((_, i) => (
          <line key={i} x1="0" y1={i*8} x2={w} y2={i*8} stroke="#fff" strokeWidth="0.4"/>
        ))}
      </g>
      {/* noise */}
      {noise.map((n, i) => (
        <circle key={i} cx={n.x} cy={n.y} r={n.r} fill="#fff" opacity={n.o} />
      ))}
      {/* digits */}
      <g transform={`translate(${pad}, ${pad})`}>
        {chars.map((c, i) => {
          const d = DigitStrokes[c] || DigitStrokes["0"];
          const rx = (rnd(i*9) - 0.5) * 6;
          const ry = (rnd(i*9+3) - 0.5) * 6;
          const rot = (rnd(i*9+5) - 0.5) * 14;
          const scale = (charW / 64);
          return (
            <g key={i} transform={`translate(${i*charW + rx}, ${ry}) rotate(${rot} ${charW/2} ${(h-pad*2)/2}) scale(${scale} ${(h-pad*2)/100})`}>
              <path d={d} stroke="#f6f5f1" strokeWidth={5 + rnd(i)*2} strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.94"/>
            </g>
          );
        })}
      </g>
      {/* vignette smudge */}
      <g opacity="0.35">
        <ellipse cx={w*0.2} cy={h*0.8} rx="22" ry="8" fill="#000"/>
        <ellipse cx={w*0.75} cy={h*0.25} rx="18" ry="6" fill="#000"/>
      </g>
    </svg>
  );
}

const SAMPLES = [
  { id: "s1", label: "Fontfre_Clean_TE", src: "/images/Fontfre_Clean_TE.png" },
  { id: "s2", label: "Fontfre_Clean_TR", src: "/images/Fontfre_Clean_TR.png" },
  { id: "s3", label: "Fontfre_Clean_VA", src: "/images/Fontfre_Clean_VA.png" },
  { id: "s4", label: "Fontfrm_Clean_TE", src: "/images/Fontfrm_Clean_TE.png" },
];

async function fetchSampleBase64(src) {
  const res = await fetch(src);
  const blob = await res.blob();
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result.split(",")[1]);
    reader.readAsDataURL(blob);
  });
}

Object.assign(window, { NoisyDigit, SAMPLES, fetchSampleBase64 });
