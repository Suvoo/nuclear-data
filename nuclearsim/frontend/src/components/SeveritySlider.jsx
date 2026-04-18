import React from "react";

const LEVELS = [
  { v: 1, label: "NOMINAL", color: "#00ff88" },
  { v: 2, label: "MINOR", color: "#00ff88" },
  { v: 3, label: "MODERATE", color: "#ffcc00" },
  { v: 4, label: "SERIOUS", color: "#ff6b00" },
  { v: 5, label: "CRITICAL", color: "#ff2244" },
];

export default function SeveritySlider({ value, onChange }) {
  const current = LEVELS.find((l) => l.v === value) || LEVELS[2];
  const pct = ((value - 1) / 4) * 100;

  return (
    <div className="space-y-3">
      <div className="relative h-2 bg-surface2 border border-border">
        <div
          className="absolute top-0 left-0 h-full transition-[width,background] duration-300"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, #00ff88 0%, #ffcc00 50%, #ff2244 100%)`,
            clipPath: `inset(0 ${100 - pct}% 0 0)`,
          }}
        />
        <input
          type="range"
          min={1}
          max={5}
          step={1}
          value={value}
          onChange={(e) => onChange(parseInt(e.target.value, 10))}
          className="absolute inset-0 w-full opacity-0 cursor-pointer"
        />
        {LEVELS.map((l) => (
          <div
            key={l.v}
            className={`absolute top-1/2 -translate-y-1/2 w-3 h-3 border-2 transition-all ${
              value >= l.v ? "border-transparent" : "border-border bg-surface"
            }`}
            style={{
              left: `calc(${((l.v - 1) / 4) * 100}% - 6px)`,
              background: value >= l.v ? l.color : undefined,
              boxShadow:
                value === l.v ? `0 0 12px ${l.color}` : undefined,
            }}
          />
        ))}
      </div>
      <div className="flex items-center justify-between font-mono text-[10px] text-txt-dim uppercase tracking-wider">
        {LEVELS.map((l) => (
          <span
            key={l.v}
            className={
              value === l.v ? "text-txt-primary font-semibold" : ""
            }
          >
            {l.v}
          </span>
        ))}
      </div>
      <div
        className="flex items-center gap-3 pt-2 border-t border-border"
        style={{ color: current.color }}
      >
        <div
          className="w-2 h-2"
          style={{ background: current.color, boxShadow: `0 0 8px ${current.color}` }}
        />
        <span className="font-mono text-xs tracking-widest uppercase">
          sev {value} / {current.label}
        </span>
      </div>
    </div>
  );
}
