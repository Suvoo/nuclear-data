import React from "react";

const OPTIONS = [
  { v: "optimal", label: "OPTIMAL" },
  { v: "dim", label: "DIM" },
  { v: "failed", label: "FAILED" },
];

export default function LightingPicker({ value, onChange }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {OPTIONS.map((o) => {
        const active = o.v === value;
        return (
          <button
            key={o.v}
            type="button"
            onClick={() => onChange(o.v)}
            className={`py-2 font-mono text-xs tracking-widest border transition-colors ${
              active
                ? "border-accent-green text-accent-green bg-accent-green/5 shadow-glow"
                : "border-border text-txt-mid hover:border-accent-green/40 hover:text-txt-primary"
            }`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
