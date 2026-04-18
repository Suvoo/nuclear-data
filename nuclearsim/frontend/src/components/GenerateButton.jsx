import React from "react";
import { Zap, Loader2 } from "lucide-react";

export default function GenerateButton({ running, onClick, disabled }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || running}
      className={`w-full flex items-center justify-center gap-3 py-4 font-mono text-sm tracking-widest uppercase border transition-all ${
        running
          ? "border-accent-green/60 text-accent-green animate-pulse-border cursor-not-allowed"
          : disabled
            ? "border-border text-txt-dim cursor-not-allowed"
            : "border-accent-green text-accent-green bg-accent-green/5 hover:bg-accent-green/10 hover:shadow-glow"
      }`}
    >
      {running ? (
        <>
          <Loader2 size={16} className="animate-spin" />
          Generating dataset…
        </>
      ) : (
        <>
          <Zap size={16} />
          Generate training data
        </>
      )}
    </button>
  );
}
