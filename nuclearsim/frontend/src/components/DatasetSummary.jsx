import React from "react";
import { Download, ShieldAlert, ShieldCheck } from "lucide-react";
import JsonViewer from "./JsonViewer.jsx";

function sevColor(sev) {
  if (sev >= 5) return "#ff2244";
  if (sev >= 4) return "#ff6b00";
  if (sev >= 3) return "#ffcc00";
  return "#00ff88";
}

function Metric({ label, value, accent = "#e0e0e0", sub }) {
  return (
    <div className="border border-border bg-surface p-4">
      <div className="font-mono text-[10px] uppercase tracking-widest text-txt-dim mb-1">
        {label}
      </div>
      <div
        className="font-mono text-3xl leading-none"
        style={{ color: accent }}
      >
        {value}
      </div>
      {sub && (
        <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-txt-mid">
          {sub}
        </div>
      )}
    </div>
  );
}

export default function DatasetSummary({ result }) {
  if (!result) return null;
  const s = result.summary || {};
  const q = result.dataset_quality || {};
  const r = result.sim_to_real_assessment || {};

  const qualityScore = Math.round(
    ((q.class_balance_score || 0) * 0.4 +
      (q.mean_confidence || 0) * 0.4 +
      (q.severity_coverage
        ? q.severity_coverage.filter((c) => c > 0).length / 5
        : 0) *
        0.2) *
      100
  );
  const qColor =
    qualityScore >= 75
      ? "#00ff88"
      : qualityScore >= 50
        ? "#ffcc00"
        : "#ff6b00";

  const realism = Math.round((r.overall_realism_score || 0) * 100);

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-mono text-xs uppercase tracking-widest text-txt-dim">
          // dataset summary
        </h2>
        <a
          href={result.download_url}
          className="inline-flex items-center gap-2 px-4 py-2 border border-accent-green text-accent-green bg-accent-green/5 hover:bg-accent-green/10 hover:shadow-glow font-mono text-xs uppercase tracking-widest transition-all"
        >
          <Download size={14} />
          Download dataset (.zip)
        </a>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric label="Total frames" value={s.total_frames ?? 0} />
        <Metric
          label="Defects detected"
          value={`${s.defects_detected ?? 0}/${s.total_frames ?? 0}`}
          accent="#ff6b00"
        />
        <Metric
          label="Max severity"
          value={s.max_severity ?? 0}
          accent={sevColor(s.max_severity ?? 0)}
          sub={s.highest_risk_action}
        />
        <Metric
          label="Quality score"
          value={`${qualityScore}`}
          accent={qColor}
          sub="/ 100"
        />
      </div>

      <div className="grid md:grid-cols-2 gap-3">
        <div className="border border-border bg-surface p-4">
          <div className="flex items-center gap-2 mb-3">
            {q.production_ready ? (
              <ShieldCheck size={14} className="text-accent-green" />
            ) : (
              <ShieldAlert size={14} className="text-accent-orange" />
            )}
            <h3 className="font-mono text-[11px] uppercase tracking-widest text-txt-dim">
              quality assessment
            </h3>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-txt-dim">Class balance</span>
              <span className="font-mono">{q.class_balance_score ?? "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-txt-dim">Mean confidence</span>
              <span className="font-mono">{q.mean_confidence ?? "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-txt-dim">Severity coverage</span>
              <span className="font-mono">
                [{(q.severity_coverage || []).join(", ")}]
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-txt-dim">Production ready</span>
              <span
                className="font-mono"
                style={{
                  color: q.production_ready ? "#00ff88" : "#ff6b00",
                }}
              >
                {q.production_ready ? "YES" : "NO"}
              </span>
            </div>
          </div>
          {q.warnings && Object.keys(q.warnings).length > 0 && (
            <ul className="mt-3 pt-3 border-t border-border space-y-1 text-xs text-accent-orange">
              {Object.entries(q.warnings).map(([k, v]) => (
                <li key={k}>! {v}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="border border-border bg-surface p-4">
          <div className="flex items-center gap-2 mb-3">
            <ShieldAlert size={14} className="text-accent-yellow" />
            <h3 className="font-mono text-[11px] uppercase tracking-widest text-txt-dim">
              sim-to-real gap
            </h3>
          </div>
          <div className="flex items-baseline gap-2">
            <span
              className="font-mono text-3xl"
              style={{
                color:
                  realism >= 70
                    ? "#00ff88"
                    : realism >= 50
                      ? "#ffcc00"
                      : "#ff6b00",
              }}
            >
              {realism}
            </span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-txt-dim">
              / 100 realism
            </span>
          </div>
          <ul className="mt-3 pt-3 border-t border-border space-y-2 text-xs">
            {(r.risk_factors || []).slice(0, 3).map((rf, i) => (
              <li key={i}>
                <div className="font-mono text-[10px] uppercase tracking-widest text-txt-dim">
                  {rf.factor}
                </div>
                <div className="text-txt-primary">{rf.issue}</div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <JsonViewer
        data={result.raw_dataset}
        title={`coco dataset // ${result.scenario}_sev${result.severity}_dataset.json`}
        downloadUrl={result.dataset_url}
        initiallyOpen={true}
        maxHeight="32rem"
      />
    </section>
  );
}
