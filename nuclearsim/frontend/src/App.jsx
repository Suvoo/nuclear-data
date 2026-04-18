import React, { useEffect, useState } from "react";
import { Atom, Info, Terminal } from "lucide-react";
import ScenarioSelector from "./components/ScenarioSelector.jsx";
import SeveritySlider from "./components/SeveritySlider.jsx";
import LightingPicker from "./components/LightingPicker.jsx";
import GenerateButton from "./components/GenerateButton.jsx";
import TerminalLog from "./components/TerminalLog.jsx";
import VideoPlayer from "./components/VideoPlayer.jsx";
import FrameGrid from "./components/FrameGrid.jsx";
import FrameModal from "./components/FrameModal.jsx";
import DatasetSummary from "./components/DatasetSummary.jsx";
import StatsPanel from "./components/StatsPanel.jsx";
import IdleOutput from "./components/IdleOutput.jsx";
import { api } from "./api.js";

export default function App() {
  const [scenarios, setScenarios] = useState([]);
  const [scenario, setScenario] = useState("pipe_crack");
  const [severity, setSeverity] = useState(3);
  const [lighting, setLighting] = useState("optimal");

  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | running | complete | failed
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const [openFrame, setOpenFrame] = useState(null);
  const [showInfo, setShowInfo] = useState(true);

  useEffect(() => {
    fetch(api("/api/scenarios"))
      .then((r) => r.json())
      .then((d) => {
        setScenarios(d.scenarios || []);
        if (d.scenarios?.length && !d.scenarios.find((s) => s.key === scenario)) {
          setScenario(d.scenarios[0].key);
        }
      })
      .catch(() =>
        setError(
          "Backend unreachable. Is your local server running and tunnel online?"
        )
      );
  }, []);

  useEffect(() => {
    if (!jobId || status !== "running") return undefined;
    let cancelled = false;
    const poll = async () => {
      try {
        const r = await fetch(api(`/api/status/${jobId}`));
        const d = await r.json();
        if (cancelled) return;
        setLogs(d.logs || []);
        setProgress(d.progress || 0);
        if (d.status === "complete") {
          const res = d.result || {};
          // Rewrite server-relative URLs so the browser hits the tunnel /
          // backend host when the frontend is deployed on a different origin.
          if (res.video_url) res.video_url = api(res.video_url);
          if (res.download_url) res.download_url = api(res.download_url);
          if (res.dataset_url) res.dataset_url = api(res.dataset_url);
          if (res.frame_url_prefix) res.frame_url_prefix = api(res.frame_url_prefix);
          setResult(res);
          setStatus("complete");
        } else if (d.status === "failed") {
          setError(d.error || "pipeline failed");
          setStatus("failed");
        }
      } catch {
        /* transient */
      }
    };
    poll();
    const iv = setInterval(poll, 1500);
    return () => {
      cancelled = true;
      clearInterval(iv);
    };
  }, [jobId, status]);

  const handleGenerate = async () => {
    setResult(null);
    setLogs([]);
    setError(null);
    setProgress(0);
    setStatus("running");
    try {
      const r = await fetch(api("/api/generate"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario, severity, lighting }),
      });
      const d = await r.json();
      if (!r.ok) {
        setError(d.detail || "failed to start");
        setStatus("failed");
        return;
      }
      setJobId(d.job_id);
    } catch (e) {
      setError(String(e));
      setStatus("failed");
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-border bg-surface/60 backdrop-blur">
        <div className="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Atom size={20} className="text-accent-green" />
            <div className="font-mono text-sm tracking-[0.3em] uppercase">
              <span className="text-accent-green">nuclear</span>
              <span className="text-txt-primary">sim</span>
            </div>
            <span className="ml-3 font-mono text-[10px] text-txt-dim uppercase tracking-widest border border-border px-2 py-0.5">
              v1.0 / synthetic perception data
            </span>
          </div>
          <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest text-txt-dim">
            <span className="flex items-center gap-1">
              <Terminal size={12} />
              status: {status}
            </span>
            {status === "running" && (
              <span className="text-accent-green">{progress}%</span>
            )}
            <button
              type="button"
              onClick={() => setShowInfo((v) => !v)}
              className="flex items-center gap-1 hover:text-txt-primary"
            >
              <Info size={12} />
              {showInfo ? "hide" : "show"} brief
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-[1600px] w-full mx-auto px-6 py-6 space-y-6">
        {/* Generator */}
        <section className="grid lg:grid-cols-[380px_1fr] gap-6">
          {/* Controls */}
          <aside className="space-y-5">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-txt-dim mb-2">
                // scenario configuration
              </div>
              <ScenarioSelector
                value={scenario}
                onChange={setScenario}
                scenarios={scenarios}
              />
            </div>

            <div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-txt-dim mb-2">
                // severity
              </div>
              <SeveritySlider value={severity} onChange={setSeverity} />
            </div>

            <div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-txt-dim mb-2">
                // lighting
              </div>
              <LightingPicker value={lighting} onChange={setLighting} />
            </div>

            <div>
              <GenerateButton
                running={status === "running"}
                onClick={handleGenerate}
                disabled={!scenario}
              />
              <div className="mt-2 font-mono text-[10px] text-txt-dim uppercase tracking-widest text-center">
                estimated time: 45&ndash;90 seconds
              </div>
              {error && (
                <div className="mt-3 border border-accent-red/50 bg-accent-red/5 p-2 font-mono text-xs text-accent-red">
                  ! {error}
                </div>
              )}
            </div>
          </aside>

          {/* Output */}
          <div className="min-h-[420px]">
            {status === "idle" && <IdleOutput />}
            {status === "failed" && (
              <div className="h-full min-h-[420px] border border-accent-red/50 bg-accent-red/5 p-4">
                <TerminalLog logs={logs.length ? logs : [error || "failed"]} running={false} />
              </div>
            )}
            {status === "running" && (
              <div className="h-full min-h-[420px]">
                <TerminalLog logs={logs} running={true} />
              </div>
            )}
            {status === "complete" && result && (
              <div className="space-y-4">
                <VideoPlayer result={result} />
                <FrameGrid result={result} onOpen={setOpenFrame} />
              </div>
            )}
          </div>
        </section>

        {/* Summary */}
        {status === "complete" && result && (
          <DatasetSummary result={result} />
        )}

        {/* Brief / Why this exists */}
        {showInfo && <StatsPanel />}
      </main>

      <footer className="border-t border-border py-4 px-6 font-mono text-[10px] uppercase tracking-widest text-txt-dim flex justify-between">
        <span>nuclearsim :: synthetic training data pipeline</span>
        <span>built for beta hacks 2026</span>
      </footer>

      <FrameModal
        frame={openFrame}
        result={result}
        onClose={() => setOpenFrame(null)}
      />
    </div>
  );
}
