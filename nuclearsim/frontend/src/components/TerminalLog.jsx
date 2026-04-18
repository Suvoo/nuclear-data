import React, { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";

function colorFor(line) {
  const l = line.toLowerCase();
  if (l.includes("error") || l.includes("failed") || l.includes("sev=5") || l.includes("halt")) {
    return "text-accent-red";
  }
  if (l.includes("sev=4") || l.includes("alert_operator") || l.includes("!")) {
    return "text-accent-orange";
  }
  if (l.startsWith("===") || l.includes("complete")) {
    return "text-accent-green font-semibold";
  }
  if (l.startsWith("[")) {
    return "text-accent-green";
  }
  return "text-txt-primary";
}

export default function TerminalLog({ logs, running }) {
  const endRef = useRef(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [logs.length]);

  return (
    <div className="relative bg-[#05050a] border border-border font-mono text-xs leading-relaxed h-full overflow-auto p-4">
      <div className="flex items-center gap-2 pb-2 mb-3 border-b border-border">
        <div className="w-2 h-2 bg-accent-red" />
        <div className="w-2 h-2 bg-accent-yellow" />
        <div className="w-2 h-2 bg-accent-green" />
        <span className="ml-2 text-txt-dim tracking-widest uppercase text-[10px]">
          nuclearsim::pipeline
        </span>
      </div>
      <AnimatePresence initial={false}>
        {logs.map((line, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.15 }}
            className={`whitespace-pre-wrap ${colorFor(line)}`}
          >
            <span className="text-txt-dim mr-2">&gt;</span>
            {line || "\u00a0"}
          </motion.div>
        ))}
      </AnimatePresence>
      {running && (
        <div className="text-accent-green terminal-caret">&nbsp;</div>
      )}
      <div ref={endRef} />
    </div>
  );
}
