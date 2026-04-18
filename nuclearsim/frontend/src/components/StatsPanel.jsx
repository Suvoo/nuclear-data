import React, { useEffect, useState } from "react";

function useCountUp(target, duration = 1400) {
  const [n, setN] = useState(0);
  useEffect(() => {
    let start = null;
    let raf;
    const step = (t) => {
      if (!start) start = t;
      const p = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(target * eased);
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return n;
}

function StatCard({ label, value, suffix = "", prefix = "", format = (v) => v }) {
  const n = useCountUp(value);
  return (
    <div className="border border-border bg-surface p-6">
      <div className="font-mono text-5xl md:text-6xl text-accent-green leading-none tracking-tight">
        {prefix}
        {format(n)}
        {suffix}
      </div>
      <div className="mt-3 font-mono text-[11px] uppercase tracking-widest text-txt-dim">
        {label}
      </div>
    </div>
  );
}

export default function StatsPanel() {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-mono text-xs uppercase tracking-widest text-txt-dim">
          // why this exists
        </h2>
        <span className="font-mono text-[10px] text-txt-dim uppercase tracking-widest">
          bloomberg-style brief
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="Operational nuclear reactors worldwide"
          value={415}
          format={(v) => Math.round(v)}
        />
        <StatCard
          label="Global decommissioning cost (USD)"
          value={650}
          prefix="$"
          suffix="B"
          format={(v) => Math.round(v)}
        />
        <StatCard
          label="Public nuclear robot vision datasets"
          value={0}
          prefix="~"
          format={() => 0}
        />
        <StatCard
          label="Seconds to generate one labeled dataset"
          value={60}
          prefix="<"
          suffix="s"
          format={(v) => Math.round(v)}
        />
      </div>
      <p className="font-mono text-xs text-txt-mid leading-relaxed max-w-3xl">
        Nuclear inspection robots need labeled vision data that effectively
        does not exist: footage is classified, defects are rare, and staging
        real hazards is impossible. NuclearSim closes that gap with
        severity-calibrated synthetic video, VLM-driven annotations, and a
        sim-to-real realism audit in a single pipeline.
      </p>
    </section>
  );
}
