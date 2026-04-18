import React from "react";

function sevColor(sev) {
  if (sev >= 5) return "#ff2244";
  if (sev >= 4) return "#ff6b00";
  if (sev >= 3) return "#ffcc00";
  return "#00ff88";
}

export default function VideoPlayer({ result }) {
  if (!result) return null;
  const sev = result.summary?.max_severity || result.severity;
  const color = sevColor(sev);
  return (
    <div className="relative border border-border bg-black">
      <video
        src={result.video_url}
        autoPlay
        muted
        loop
        playsInline
        controls
        className="w-full block"
      />
      <div className="absolute top-3 left-3 px-2 py-1 bg-black/80 border border-border font-mono text-[10px] uppercase tracking-widest text-txt-primary">
        {result.scenario_label || result.scenario}
      </div>
      <div
        className="absolute top-3 right-3 px-2 py-1 bg-black/80 border font-mono text-[10px] uppercase tracking-widest"
        style={{ borderColor: color, color }}
      >
        sev {sev}
      </div>
    </div>
  );
}
