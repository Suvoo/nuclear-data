import React, { useEffect, useRef, useState } from "react";
import { ChevronDown, Check } from "lucide-react";

export default function ScenarioSelector({ value, onChange, scenarios }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    window.addEventListener("mousedown", handler);
    return () => window.removeEventListener("mousedown", handler);
  }, []);

  const selected = scenarios.find((s) => s.key === value);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-surface border border-border hover:border-accent-green/40 transition-colors text-left"
      >
        <span className="flex flex-col">
          <span className="font-mono text-xs text-txt-dim uppercase tracking-wider">
            {selected ? selected.key : "select scenario"}
          </span>
          <span className="text-sm text-txt-primary">
            {selected ? selected.label : "—"}
          </span>
        </span>
        <ChevronDown
          size={16}
          className={`text-txt-mid transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-full bg-surface border border-border shadow-2xl max-h-80 overflow-auto">
          {scenarios.map((s) => {
            const active = s.key === value;
            return (
              <button
                key={s.key}
                type="button"
                onClick={() => {
                  onChange(s.key);
                  setOpen(false);
                }}
                className={`w-full flex items-center justify-between px-4 py-2.5 text-left border-l-2 transition-colors ${
                  active
                    ? "bg-surface2 border-accent-green text-txt-primary"
                    : "border-transparent hover:bg-surface2 hover:border-accent-green/40 text-txt-primary"
                }`}
              >
                <span className="flex flex-col">
                  <span className="font-mono text-xs text-txt-dim uppercase tracking-wider">
                    {s.key}
                  </span>
                  <span className="text-sm">{s.label}</span>
                </span>
                <div className="flex items-center gap-2">
                  {s.complexity === "compound" && (
                    <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 border border-accent-orange/50 text-accent-orange">
                      compound
                    </span>
                  )}
                  {active && (
                    <Check size={14} className="text-accent-green" />
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
