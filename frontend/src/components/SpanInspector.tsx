import type { Span } from "./SpanTree";

interface SpanInspectorProps {
  selectedSpan: Span | null;
  formatDuration: (ms: number | null) => string;
  formatCost: (cost: number) => string;
}

export function SpanInspector({ selectedSpan, formatDuration, formatCost }: SpanInspectorProps) {
  if (!selectedSpan) {
    return (
      <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)" }}>
        Select a span from the left cascade tree to inspect parameters and outputs.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid var(--border-color)", paddingBottom: "16px", marginBottom: "16px" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: 700 }}>{selectedSpan.name}</h2>
          <div style={{ display: "flex", gap: "10px", marginTop: "6px", fontSize: "12px", color: "var(--text-secondary)" }}>
            <span>Provider: <strong style={{ color: "var(--text-primary)" }}>{selectedSpan.provider || "N/A"}</strong></span>
            <span>•</span>
            <span>Model: <strong style={{ color: "var(--text-primary)" }}>{selectedSpan.model || "N/A"}</strong></span>
          </div>
        </div>
        <span className={`badge ${selectedSpan.status}`}>
          {selectedSpan.status}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "20px" }}>
        <div style={{ backgroundColor: "rgba(255,255,255,0.03)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
          <span style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>Duration</span>
          <div style={{ fontSize: "16px", fontWeight: 600, marginTop: "4px" }}>{formatDuration(selectedSpan.duration_ms)}</div>
        </div>
        <div style={{ backgroundColor: "rgba(255,255,255,0.03)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
          <span style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>Tokens</span>
          <div style={{ fontSize: "16px", fontWeight: 600, marginTop: "4px" }}>
            {selectedSpan.total_tokens || 0}
            <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 400, marginLeft: "4px" }}>
              ({selectedSpan.prompt_tokens} in / {selectedSpan.completion_tokens} out)
            </span>
          </div>
        </div>
        <div style={{ backgroundColor: "rgba(255,255,255,0.03)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
          <span style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase" }}>Span Cost</span>
          <div style={{ fontSize: "16px", fontWeight: 600, marginTop: "4px", color: "#a78bfa" }}>{formatCost(selectedSpan.cost_usd)}</div>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "16px", flexGrow: 1, overflowY: "auto", maxHeight: "40vh" }}>
        {selectedSpan.input_preview && (
          <div>
            <span style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px", color: "var(--text-secondary)" }}>Prompt Input</span>
            <div style={{ backgroundColor: "rgba(0,0,0,0.2)", border: "1px solid var(--border-color)", padding: "12px", borderRadius: "6px", fontSize: "13px", fontFamily: "monospace", whiteSpace: "pre-wrap" }}>
              {selectedSpan.input_preview}
            </div>
          </div>
        )}

        {selectedSpan.output_preview && (
          <div>
            <span style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px", color: "var(--text-secondary)" }}>Response Output</span>
            <div style={{ backgroundColor: "rgba(0,0,0,0.2)", border: "1px solid var(--border-color)", padding: "12px", borderRadius: "6px", fontSize: "13px", fontFamily: "monospace", whiteSpace: "pre-wrap" }}>
              {selectedSpan.output_preview}
            </div>
          </div>
        )}

        {selectedSpan.error_message && (
          <div>
            <span style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px", color: "var(--status-error)" }}>Error ({selectedSpan.error_type || "Fail"})</span>
            <div style={{ backgroundColor: "var(--status-error-bg)", border: "1px solid rgba(244, 63, 94, 0.2)", padding: "12px", borderRadius: "6px", fontSize: "13px", color: "var(--status-error)", fontFamily: "monospace" }}>
              {selectedSpan.error_message}
            </div>
          </div>
        )}

        <div>
          <span style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px", color: "var(--text-secondary)" }}>Raw Details & Metadata</span>
          <pre style={{ backgroundColor: "rgba(0,0,0,0.3)", border: "1px solid var(--border-color)", padding: "12px", borderRadius: "6px", fontSize: "12px", fontFamily: "monospace", overflowX: "auto" }}>
            {JSON.stringify({
              span_id: selectedSpan.span_id,
              parent_span_id: selectedSpan.parent_span_id,
              span_type: selectedSpan.span_type,
              tool_name: selectedSpan.tool_name,
              tool_input: selectedSpan.tool_input,
              tool_output: selectedSpan.tool_output,
              metadata: selectedSpan.metadata
            }, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
