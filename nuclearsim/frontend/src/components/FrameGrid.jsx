import React from "react";
import { motion } from "framer-motion";

function sevColor(sev) {
  if (sev >= 5) return "#ff2244";
  if (sev >= 4) return "#ff6b00";
  if (sev >= 3) return "#ffcc00";
  return "#00ff88";
}

export default function FrameGrid({ result, onOpen }) {
  if (!result) return null;
  const frames = result.frames || [];
  const prefix = result.frame_url_prefix;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {frames.map((f, i) => {
        const sev = f.severity || 1;
        const color = sevColor(sev);
        const glow = f.defect_detected
          ? `0 0 12px ${color}99, inset 0 0 0 1px ${color}`
          : "inset 0 0 0 1px #1e1e2e";
        return (
          <motion.button
            key={f.id}
            type="button"
            onClick={() => onOpen(f)}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i * 0.04, 0.6), duration: 0.3 }}
            className="relative bg-surface group overflow-hidden"
            style={{ boxShadow: glow }}
          >
            <img
              src={`${prefix}/${f.file_name}`}
              alt={f.file_name}
              className="w-full aspect-video object-cover block group-hover:scale-[1.02] transition-transform"
            />
            <div className="absolute top-1.5 left-1.5 px-1.5 py-0.5 bg-black/75 border border-border font-mono text-[9px] uppercase tracking-wider text-txt-primary">
              {f.defect_type}
            </div>
            <div
              className="absolute top-1.5 right-1.5 px-1.5 py-0.5 bg-black/75 border font-mono text-[9px] uppercase tracking-wider"
              style={{ borderColor: color, color }}
            >
              s{sev}
            </div>
            <div className="absolute bottom-0 inset-x-0 px-2 py-1 bg-black/80 font-mono text-[9px] uppercase tracking-wider text-txt-dim flex justify-between">
              <span>#{f.frame_number}</span>
              <span style={{ color }}>{f.recommended_action}</span>
            </div>
          </motion.button>
        );
      })}
    </div>
  );
}
