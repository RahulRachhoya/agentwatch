import { ChevronRight, ChevronDown } from "lucide-react";

export interface Span {
  id?: number;
  span_id: string;
  run_id: string;
  parent_span_id: string | null;
  span_type: string;
  name: string;
  model: string | null;
  provider: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  input_preview: string | null;
  output_preview: string | null;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  status: string;
  error_type: string | null;
  error_message: string | null;
  tool_name: string | null;
  tool_input: any;
  tool_output: any;
  metadata: any;
}

interface SpanNodeProps {
  span: Span;
  allSpans: Span[];
  depth: number;
  expandedSpans: Record<string, boolean>;
  selectedSpan: Span | null;
  onToggleExpand: (spanId: string) => void;
  onSelectSpan: (span: Span) => void;
  formatDuration: (ms: number | null) => string;
}

function SpanNode({
  span,
  allSpans,
  depth,
  expandedSpans,
  selectedSpan,
  onToggleExpand,
  onSelectSpan,
  formatDuration
}: SpanNodeProps) {
  const children = allSpans.filter(s => s.parent_span_id === span.span_id);
  const hasChildren = children.length > 0;
  const isExpanded = expandedSpans[span.span_id] ?? true;

  const toggleExpand = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleExpand(span.span_id);
  };

  const isSelected = selectedSpan?.span_id === span.span_id;

  const getSpanTypeStyles = (type: string) => {
    switch (type) {
      case "llm": return { bg: "rgba(139, 92, 246, 0.12)", color: "#a78bfa", label: "LLM" };
      case "tool": return { bg: "rgba(59, 130, 246, 0.12)", color: "#60a5fa", label: "Tool" };
      case "chain": return { bg: "rgba(16, 185, 129, 0.12)", color: "#34d399", label: "Chain" };
      default: return { bg: "rgba(107, 114, 128, 0.12)", color: "#9ca3af", label: "Span" };
    }
  };

  const styles = getSpanTypeStyles(span.span_type);

  return (
    <div style={{ marginLeft: `${depth * 14}px` }}>
      <div
        onClick={() => onSelectSpan(span)}
        className={`span-tree-row ${isSelected ? "selected" : ""}`}
        style={{
          display: "flex",
          alignItems: "center",
          padding: "8px 12px",
          borderRadius: "6px",
          cursor: "pointer",
          marginBottom: "4px",
          background: isSelected ? "rgba(139, 92, 246, 0.15)" : "transparent",
          border: isSelected ? "1px solid rgba(139, 92, 246, 0.3)" : "1px solid transparent",
          transition: "var(--transition)"
        }}
      >
        <div style={{ width: "20px", display: "flex", justifyContent: "center" }}>
          {hasChildren && (
            <span onClick={toggleExpand} style={{ display: "inline-flex", cursor: "pointer" }}>
              {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </span>
          )}
        </div>

        <span
          style={{
            fontSize: "10px",
            fontWeight: 700,
            backgroundColor: styles.bg,
            color: styles.color,
            padding: "2px 6px",
            borderRadius: "4px",
            marginRight: "10px",
            letterSpacing: "0.03em"
          }}
        >
          {styles.label}
        </span>

        <span style={{ fontWeight: 500, fontSize: "13px", color: isSelected ? "var(--text-primary)" : "#d1d5db", flexGrow: 1 }}>
          {span.name} {span.model && <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 400 }}>({span.model})</span>}
        </span>

        <span style={{ fontSize: "11px", color: "var(--text-secondary)", marginLeft: "12px" }}>
          {formatDuration(span.duration_ms)}
        </span>

        <div
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            backgroundColor: span.status === "success" ? "var(--status-success)" : span.status === "error" ? "var(--status-error)" : "var(--status-running)",
            marginLeft: "12px"
          }}
        />
      </div>

      {hasChildren && isExpanded && (
        <div className="span-tree-children">
          {children.map(child => (
            <SpanNode
              key={child.span_id}
              span={child}
              allSpans={allSpans}
              depth={depth + 1}
              expandedSpans={expandedSpans}
              selectedSpan={selectedSpan}
              onToggleExpand={onToggleExpand}
              onSelectSpan={onSelectSpan}
              formatDuration={formatDuration}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface SpanTreeProps {
  spans: Span[];
  expandedSpans: Record<string, boolean>;
  selectedSpan: Span | null;
  onToggleExpand: (spanId: string) => void;
  onSelectSpan: (span: Span) => void;
  formatDuration: (ms: number | null) => string;
}

export function SpanTree({
  spans,
  expandedSpans,
  selectedSpan,
  onToggleExpand,
  onSelectSpan,
  formatDuration
}: SpanTreeProps) {
  if (!spans || spans.length === 0) {
    return <div style={{ color: "var(--text-secondary)", padding: "16px" }}>No spans recorded for this run.</div>;
  }

  const spanIds = spans.map(s => s.span_id);
  const roots = spans.filter(s => !s.parent_span_id || !spanIds.includes(s.parent_span_id));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
      {roots.map(root => (
        <SpanNode
          key={root.span_id}
          span={root}
          allSpans={spans}
          depth={0}
          expandedSpans={expandedSpans}
          selectedSpan={selectedSpan}
          onToggleExpand={onToggleExpand}
          onSelectSpan={onSelectSpan}
          formatDuration={formatDuration}
        />
      ))}
    </div>
  );
}
