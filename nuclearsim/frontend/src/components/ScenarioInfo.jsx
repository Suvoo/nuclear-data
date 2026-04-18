import React from "react";
import { Info } from "lucide-react";

const SCENARIO_INFO = {
  pipe_crack: {
    title: "Pipe Crack Detection",
    what: "Synthetic footage of coolant and service piping with hairline fractures, stress fissures, or active leaks along weld seams and pipe bodies.",
    why: "Undetected cracks in a nuclear facility can escalate into coolant loss, radioactive steam release, or pressure boundary failure. Early visual detection is critical before a micro-crack becomes a rupture.",
    lookingFor:
      "Train perception models to localize thin linear defects, drip trails, and moisture halos on metallic surfaces under plant lighting.",
  },
  flooded_basement: {
    title: "Flooded Basement / Water Ingress",
    what: "Lower-level plant rooms with standing water, submerged equipment, reflective surfaces, and partial obstruction of access routes.",
    why: "Flooding in containment sublevels can short electrical systems, block emergency egress, and indicate a primary loop or service-water leak upstream. Water also distorts radiation readings and camera perception.",
    lookingFor:
      "Models that can segment water lines, detect submerged hazards, and stay robust to reflections and refraction around instrumentation.",
  },
  gauge_anomaly: {
    title: "Gauge / Instrument Anomaly",
    what: "Close-up views of analog and digital gauges — pressure, temperature, flow — with needles in red zones, cracked faces, or fogged displays.",
    why: "Control rooms and field panels rely on dozens of gauges. A single unread out-of-range reading can mask a developing incident. Automated gauge reading adds a redundant safety layer alongside human operators.",
    lookingFor:
      "Datasets for OCR and dial-reading models that must recognize anomalous states, not just nominal values.",
  },
  weld_inspection: {
    title: "Weld Inspection",
    what: "Macro views of structural and pipe welds, including clean passes, porosity, undercut, spatter, and incomplete fusion defects.",
    why: "Welds are the most common failure point in pressurized nuclear systems. Defective welds under thermal and radiation stress can propagate cracks that threaten the pressure boundary.",
    lookingFor:
      "Defect-classification training data that distinguishes cosmetic marks from structurally significant flaws.",
  },
  radiation_hotspot: {
    title: "Radiation Zone / Hotspot Mapping",
    what: "Scenes of corridors, valves, and equipment overlaid with visual indicators of elevated dose — contamination spread, shielding gaps, and posted radiation zones.",
    why: "Radiation is invisible. Mapping hotspots visually (via correlated sensor overlays and environmental cues) lets robots and personnel plan ALARA routes, avoid unnecessary exposure, and prioritize decontamination.",
    lookingFor:
      "Models that fuse visual scene understanding with radiation-field cues to flag no-go zones and recommend safer traversal paths.",
  },
  corridor_multiple_hazards: {
    title: "Corridor with Multiple Hazards",
    what: "A single corridor scene combining several failure modes at once — e.g. a leaking pipe, water on the floor, a gauge in alarm, and an active radiation zone.",
    why: "Real incidents rarely present one clean hazard. Compound scenarios stress-test whether a model can detect and rank multiple concurrent risks instead of locking onto the most obvious one.",
    lookingFor:
      "Robust multi-label detection and hazard-prioritization behavior under realistic, cluttered plant conditions.",
  },
};

export default function ScenarioInfo({ scenarioKey, fallbackLabel }) {
  const info = SCENARIO_INFO[scenarioKey];
  if (!info) {
    if (!scenarioKey) return null;
    return (
      <div className="border border-border bg-surface/40 p-3 font-mono text-[11px] text-txt-dim">
        <div className="flex items-center gap-1.5 uppercase tracking-widest text-[10px] mb-1">
          <Info size={11} className="text-accent-green" />
          scenario brief
        </div>
        <div className="text-txt-mid leading-relaxed">
          {fallbackLabel || scenarioKey} — no extended description available yet.
        </div>
      </div>
    );
  }

  return (
    <div className="border border-border bg-surface/40 p-3 space-y-2">
      <div className="flex items-center gap-1.5 font-mono uppercase tracking-widest text-[10px] text-txt-dim">
        <Info size={11} className="text-accent-green" />
        scenario brief
      </div>
      <div className="text-sm text-txt-primary font-medium">{info.title}</div>
      <p className="text-xs text-txt-mid leading-relaxed">
        <span className="font-mono text-[10px] uppercase tracking-widest text-accent-green mr-1">
          what
        </span>
        {info.what}
      </p>
      <p className="text-xs text-txt-mid leading-relaxed">
        <span className="font-mono text-[10px] uppercase tracking-widest text-accent-orange mr-1">
          why it matters
        </span>
        {info.why}
      </p>
      <p className="text-xs text-txt-mid leading-relaxed">
        <span className="font-mono text-[10px] uppercase tracking-widest text-txt-dim mr-1">
          what we train for
        </span>
        {info.lookingFor}
      </p>
    </div>
  );
}
