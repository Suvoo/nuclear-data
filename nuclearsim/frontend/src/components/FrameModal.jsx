import React, { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import JsonViewer from "./JsonViewer.jsx";

export default function FrameModal({ frame, result, onClose }) {
  useEffect(() => {
    const k = (e) => e.key === "Escape" && onClose();
    if (frame) window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [frame, onClose]);

  return (
    <AnimatePresence>
      {frame && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-6"
        >
          <motion.div
            initial={{ scale: 0.96, y: 10 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.96, y: 10 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-surface border border-border max-w-6xl w-full max-h-[90vh] overflow-auto"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <div className="font-mono text-xs uppercase tracking-widest text-txt-dim">
                frame #{frame.frame_number} / {frame.file_name}
              </div>
              <button
                type="button"
                onClick={onClose}
                className="text-txt-mid hover:text-txt-primary"
              >
                <X size={18} />
              </button>
            </div>
            <div className="grid md:grid-cols-2 gap-0">
              <div className="bg-black">
                <img
                  src={`${result.frame_url_prefix}/${frame.file_name}`}
                  alt=""
                  className="w-full block"
                />
              </div>
              <div className="p-4 space-y-4">
                <JsonViewer
                  data={{
                    defect_detected: frame.defect_detected,
                    defect_type: frame.defect_type,
                    severity: frame.severity,
                    location_in_frame: frame.location_in_frame,
                    recommended_action: frame.recommended_action,
                    confidence: frame.confidence,
                    defects: frame.defects,
                    reasoning: frame.reasoning,
                  }}
                  title={`annotation // frame_${frame.frame_number}`}
                  initiallyOpen={true}
                  maxHeight="18rem"
                />
                {frame.action_protocol && (
                  <section>
                    <h4 className="font-mono text-[10px] uppercase tracking-widest text-txt-dim mb-2">
                      action protocol
                    </h4>
                    <div className="text-sm space-y-2">
                      <p className="text-txt-primary">
                        {frame.action_protocol.description}
                      </p>
                      <div className="font-mono text-[11px] text-txt-mid">
                        <div>
                          <span className="text-txt-dim">robot: </span>
                          {frame.action_protocol.robot_behavior}
                        </div>
                        <div>
                          <span className="text-txt-dim">notify: </span>
                          {frame.action_protocol.human_notification || "—"}
                        </div>
                        <div>
                          <span className="text-txt-dim">escalate: </span>
                          {frame.action_protocol.escalation_time || "—"}
                        </div>
                      </div>
                    </div>
                  </section>
                )}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
