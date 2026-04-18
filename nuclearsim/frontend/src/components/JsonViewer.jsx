import React, { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Copy, Check, Download, Braces } from "lucide-react";

function syntaxHighlight(obj) {
  const json = JSON.stringify(obj, null, 2);
  // Escape HTML first.
  const escaped = json
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return escaped.replace(
    /("(\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(\.\d+)?([eE][+-]?\d+)?)/g,
    (match) => {
      let cls = "text-accent-green"; // number
      if (/^"/.test(match)) {
        cls = /:$/.test(match)
          ? "text-[#7dd3fc]" // key
          : "text-accent-orange"; // string value
      } else if (/true|false/.test(match)) {
        cls = "text-[#c084fc]";
      } else if (/null/.test(match)) {
        cls = "text-txt-dim";
      }
      return `<span class="${cls}">${match}</span>`;
    }
  );
}

export default function JsonViewer({
  data,
  title = "dataset.json",
  downloadUrl,
  initiallyOpen = false,
  maxHeight = "28rem",
}) {
  const [open, setOpen] = useState(initiallyOpen);
  const [copied, setCopied] = useState(false);

  const html = useMemo(
    () => (data ? syntaxHighlight(data) : ""),
    [data]
  );
  const rawText = useMemo(
    () => (data ? JSON.stringify(data, null, 2) : ""),
    [data]
  );

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(rawText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  };

  if (!data) return null;

  return (
    <div className="border border-border bg-surface">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-2 text-left"
        >
          <ChevronDown
            size={14}
            className={`text-txt-mid transition-transform ${
              open ? "" : "-rotate-90"
            }`}
          />
          <Braces size={14} className="text-accent-green" />
          <span className="font-mono text-[11px] uppercase tracking-widest text-txt-dim">
            {title}
          </span>
          <span className="font-mono text-[10px] text-txt-mid ml-1">
            ({(rawText.length / 1024).toFixed(1)} kB)
          </span>
        </button>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={copy}
            className="flex items-center gap-1 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-txt-mid hover:text-accent-green hover:border-accent-green/40 border border-border"
          >
            {copied ? (
              <>
                <Check size={11} /> copied
              </>
            ) : (
              <>
                <Copy size={11} /> copy
              </>
            )}
          </button>
          {downloadUrl && (
            <a
              href={downloadUrl}
              className="flex items-center gap-1 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-txt-mid hover:text-accent-green hover:border-accent-green/40 border border-border"
            >
              <Download size={11} />
              json
            </a>
          )}
        </div>
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <pre
              className="font-mono text-[11px] leading-relaxed p-4 overflow-auto bg-[#05050a] text-txt-primary"
              style={{ maxHeight }}
              // eslint-disable-next-line react/no-danger
              dangerouslySetInnerHTML={{ __html: html }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
