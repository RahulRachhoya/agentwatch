import { ChevronRight, Layers } from "lucide-react";
import { SpanTree, type Span } from "./SpanTree";
import { SpanInspector } from "./SpanInspector";

interface RunDetailsViewProps {
  runName: string | null;
  spans: Span[];
  selectedSpan: Span | null;
  expandedSpans: Record<string, boolean>;
  onBack: () => void;
  onToggleExpand: (spanId: string) => void;
  onSelectSpan: (span: Span) => void;
  formatDuration: (ms: number | null) => string;
  formatCost: (cost: number) => string;
}

export function RunDetailsView({
  runName,
  spans,
  selectedSpan,
  expandedSpans,
  onBack,
  onToggleExpand,
  onSelectSpan,
  formatDuration,
  formatCost
}: RunDetailsViewProps) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "20px" }}>
        <button
          onClick={onBack}
          style={{ color: "var(--text-secondary)", fontSize: "14px", display: "flex", alignItems: "center", gap: "4px", cursor: "pointer" }}
        >
          <ChevronRight size={16} style={{ transform: "rotate(180deg)" }} />
          <span>Back to Runs</span>
        </button>
        <span style={{ color: "var(--text-muted)" }}>/</span>
        <span style={{ fontWeight: 600 }}>{runName || "Inspect Trace"}</span>
      </div>

      <div style={{ display: "flex", gap: "24px", alignItems: "stretch" }}>
        <div className="glass-panel" style={{ width: "45%", padding: "24px", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", paddingBottom: "16px", borderBottom: "1px solid var(--border-color)", marginBottom: "16px" }}>
            <Layers size={18} color="var(--primary)" />
            <h3 style={{ fontSize: "16px", fontWeight: 600 }}>Trace Waterfall Cascade</h3>
          </div>

          <div style={{ flexGrow: 1, overflowY: "auto", maxHeight: "65vh" }}>
            <SpanTree
              spans={spans}
              expandedSpans={expandedSpans}
              selectedSpan={selectedSpan}
              onToggleExpand={onToggleExpand}
              onSelectSpan={onSelectSpan}
              formatDuration={formatDuration}
            />
          </div>
        </div>

        <div className="glass-panel" style={{ width: "55%", padding: "24px", display: "flex", flexDirection: "column" }}>
          <SpanInspector
            selectedSpan={selectedSpan}
            formatDuration={formatDuration}
            formatCost={formatCost}
          />
        </div>
      </div>
    </div>
  );
}
