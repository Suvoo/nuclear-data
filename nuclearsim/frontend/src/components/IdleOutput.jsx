import React from "react";
import { Radiation } from "lucide-react";

export default function IdleOutput() {
  return (
    <div className="relative h-full min-h-[400px] border border-dashed border-border grid-pattern flex items-center justify-center overflow-hidden">
      <div className="scanline-overlay" />
      <div className="relative text-center space-y-3">
        <Radiation
          size={40}
          className="mx-auto text-accent-green/50 animate-pulse"
        />
        <div className="font-mono text-xs uppercase tracking-[0.35em] text-txt-dim">
          awaiting generation
        </div>
        <div className="font-mono text-[10px] text-txt-dim/70 tracking-widest">
          configure scenario &middot; severity &middot; lighting
        </div>
      </div>
    </div>
  );
}
