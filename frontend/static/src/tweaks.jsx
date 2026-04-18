const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "pipelineVariant": "stepper",
  "showConsole": true,
  "accent": "teal"
}/*EDITMODE-END*/;

const ACCENTS = {
  teal:   "oklch(0.62 0.12 210)",
  indigo: "oklch(0.55 0.15 275)",
  ochre:  "oklch(0.68 0.13 75)",
  graph:  "oklch(0.30 0.02 260)"
};

function useTweaks(){
  const [values, setValues] = React.useState(TWEAK_DEFAULTS);
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    const onMsg = (e) => {
      const d = e.data || {};
      if (d.type === "__activate_edit_mode") setVisible(true);
      if (d.type === "__deactivate_edit_mode") setVisible(false);
    };
    window.addEventListener("message", onMsg);
    try { window.parent.postMessage({ type: "__edit_mode_available" }, "*"); } catch {}
    return () => window.removeEventListener("message", onMsg);
  }, []);

  React.useEffect(() => {
    document.documentElement.style.setProperty("--accent", ACCENTS[values.accent] || ACCENTS.teal);
    const hue = { teal: 210, indigo: 275, ochre: 75, graph: 260 }[values.accent] || 210;
    document.documentElement.style.setProperty("--accent-soft", `oklch(0.92 0.04 ${hue})`);
  }, [values.accent]);

  const update = (patch) => {
    const next = { ...values, ...patch };
    setValues(next);
    try {
      window.parent.postMessage({ type: "__edit_mode_set_keys", edits: patch }, "*");
    } catch {}
  };

  return { values, visible, update };
}

function TweaksPanel({ values, visible, update }){
  return (
    <div className={`tweaks-panel ${visible ? "" : "hidden"}`}>
      <div className="tweaks-head">
        <span>Tweaks</span>
        <span style={{ opacity: 0.5 }}>CRISP</span>
      </div>
      <div className="tweaks-body">
        <div className="tweak-row">
          <div className="tlbl">Pipeline Visual</div>
          <div className="seg">
            {[
              ["stepper", "Stepper"],
              ["network", "Network"],
              ["timeline", "Timeline"]
            ].map(([k, label]) => (
              <button key={k} className={values.pipelineVariant === k ? "on" : ""}
                onClick={() => update({ pipelineVariant: k })}>{label}</button>
            ))}
          </div>
        </div>
        <div className="tweak-row">
          <div className="tlbl">Accent</div>
          <div className="seg">
            {[
              ["teal","Teal"],
              ["indigo","Indigo"],
              ["ochre","Ochre"],
              ["graph","Graphite"]
            ].map(([k, label]) => (
              <button key={k} className={values.accent === k ? "on" : ""}
                onClick={() => update({ accent: k })}>{label}</button>
            ))}
          </div>
        </div>
        <div className="tweak-row">
          <div className="tlbl">Request Log</div>
          <div className="seg">
            <button className={values.showConsole ? "on" : ""} onClick={() => update({ showConsole: true })}>Visible</button>
            <button className={!values.showConsole ? "on" : ""} onClick={() => update({ showConsole: false })}>Hidden</button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { useTweaks, TweaksPanel });
