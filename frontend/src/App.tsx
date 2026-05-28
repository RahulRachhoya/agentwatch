import React, { useState, useEffect, useMemo } from "react";
import { 
  Activity, Database, Settings, Terminal, ShieldAlert, Cpu, BarChart3, 
  Search, Play, AlertCircle, CheckCircle2, Clock, DollarSign, List,
  ChevronRight, ChevronDown, Copy, RefreshCw, Layers
} from "lucide-react";
import { useWebSocket } from "./hooks/useWebSocket";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

// Interfaces
interface Span {
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

interface Run {
  id?: number;
  run_id: string;
  name: string;
  session_id: string | null;
  tags: string[] | string;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  status: string;
  error_message: string | null;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_cost_usd: number;
  span_count: number;
  tool_call_count: number;
  metadata: any;
  spans?: Span[];
}

export default function App() {
  const [activeTab, setActiveTab] = useState<"runs" | "metrics" | "settings">("runs");
  
  // Settings state
  const [backendUrl, setBackendUrl] = useState(() => {
    return localStorage.getItem("aw_backend_url") || "http://localhost:8000";
  });
  const [apiKey, setApiKey] = useState(() => {
    return localStorage.getItem("aw_api_key") || "";
  });

  // Dashboard state
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRunDetails, setSelectedRunDetails] = useState<Run | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSpans, setExpandedSpans] = useState<Record<string, boolean>>({});

  // Save config
  const saveConfig = (url: string, key: string) => {
    localStorage.setItem("aw_backend_url", url);
    localStorage.setItem("aw_api_key", key);
    setBackendUrl(url);
    setApiKey(key);
    fetchRuns();
  };

  // Headers for HTTP API
  const getHeaders = () => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json"
    };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }
    return headers;
  };

  // Fetch runs list
  const fetchRuns = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${backendUrl}/v1/runs?limit=100`, {
        headers: getHeaders()
      });
      if (!res.ok) {
        throw new Error(`Server returned status: ${res.status}`);
      }
      const json = await res.json();
      setRuns(json.data || []);
    } catch (e: any) {
      setError(`Failed to fetch runs: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Fetch selected run details
  const fetchRunDetails = async (runId: string) => {
    try {
      const res = await fetch(`${backendUrl}/v1/runs/${runId}`, {
        headers: getHeaders()
      });
      if (res.ok) {
        const json = await res.json();
        const runData = json.data;
        setSelectedRunDetails(runData);
        // Default select root span if spans exist
        if (runData.spans && runData.spans.length > 0) {
          // Find root span (no parent or parent not present in spans list)
          const spanIds = runData.spans.map((s: Span) => s.span_id);
          const rootSpan = runData.spans.find((s: Span) => !s.parent_span_id || !spanIds.includes(s.parent_span_id)) || runData.spans[0];
          setSelectedSpan(rootSpan);
        } else {
          setSelectedSpan(null);
        }
      }
    } catch (e) {
      console.error("Error fetching run details:", e);
    }
  };

  // Initialize
  useEffect(() => {
    fetchRuns();
  }, [backendUrl, apiKey]);

  // Refetch details when selectedRunId changes
  useEffect(() => {
    if (selectedRunId) {
      fetchRunDetails(selectedRunId);
    } else {
      setSelectedRunDetails(null);
      setSelectedSpan(null);
    }
  }, [selectedRunId]);

  // Connect WebSockets
  useWebSocket(backendUrl, (msg) => {
    console.log("WebSocket event received:", msg);
    const { type, data } = msg;

    if (type === "run_started") {
      setRuns((prev) => {
        // Prevent duplicate insertions
        if (prev.some((r) => r.run_id === data.run_id)) return prev;
        return [
          {
            ...data,
            total_tokens: 0,
            prompt_tokens: 0,
            completion_tokens: 0,
            total_cost_usd: 0.0,
            span_count: 0,
            tool_call_count: 0,
            status: "running"
          },
          ...prev
        ];
      });
    } else if (type === "run_completed") {
      setRuns((prev) =>
        prev.map((r) => (r.run_id === data.run_id ? { ...r, ...data } : r))
      );
      if (selectedRunId === data.run_id) {
        fetchRunDetails(data.run_id);
      }
    } else if (type === "span_created") {
      // Trigger a reload of selected run details if current run is updated
      if (selectedRunId === data.run_id) {
        fetchRunDetails(data.run_id);
      }
      // Reload runs list to update totals
      fetchRuns();
    }
  });

  // Memoized stats calculation
  const stats = useMemo(() => {
    const totalRuns = runs.length;
    const completedRuns = runs.filter(r => r.status === "success");
    const errorRuns = runs.filter(r => r.status === "error");
    const totalCost = runs.reduce((acc, r) => acc + Number(r.total_cost_usd || 0), 0);
    const totalSpans = runs.reduce((acc, r) => acc + (r.span_count || 0), 0);
    
    // Average latency
    const successfulDurations = completedRuns.filter(r => r.duration_ms).map(r => r.duration_ms as number);
    const avgLatency = successfulDurations.length 
      ? Math.round(successfulDurations.reduce((acc, val) => acc + val, 0) / successfulDurations.length)
      : 0;

    return { totalRuns, errorRuns: errorRuns.length, totalCost, totalSpans, avgLatency };
  }, [runs]);

  // Filter runs list
  const filteredRuns = useMemo(() => {
    return runs.filter(run => {
      const nameMatch = run.name.toLowerCase().includes(searchQuery.toLowerCase());
      const sessionMatch = run.session_id?.toLowerCase().includes(searchQuery.toLowerCase());
      
      // Parse tags
      let tagsStr = "";
      if (typeof run.tags === "string") {
        tagsStr = run.tags;
      } else if (Array.isArray(run.tags)) {
        tagsStr = run.tags.join(" ");
      }
      const tagsMatch = tagsStr.toLowerCase().includes(searchQuery.toLowerCase());
      
      return nameMatch || sessionMatch || tagsMatch;
    });
  }, [runs, searchQuery]);

  // Format tags string for list display
  const formatTags = (tags: any): string[] => {
    if (!tags) return [];
    if (Array.isArray(tags)) return tags;
    try {
      const parsed = JSON.parse(tags.replace(/'/g, '"'));
      if (Array.isArray(parsed)) return parsed;
    } catch (_) {}
    return typeof tags === "string" ? tags.split(",").map(t => t.trim()).filter(Boolean) : [];
  };

  // Helper formatting values
  const formatCost = (cost: number) => {
    if (cost === 0) return "$0.000000";
    return `$${cost.toFixed(6)}`;
  };

  const formatDuration = (ms: number | null) => {
    if (ms === null) return "Running";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  // Recursively Render Span Tree Components
  const SpanNode: React.FC<{ span: Span; allSpans: Span[]; depth: number }> = ({ span, allSpans, depth }) => {
    const children = allSpans.filter(s => s.parent_span_id === span.span_id);
    const hasChildren = children.length > 0;
    const isExpanded = expandedSpans[span.span_id] ?? true;

    const toggleExpand = (e: React.MouseEvent) => {
      e.stopPropagation();
      setExpandedSpans(prev => ({ ...prev, [span.span_id]: !isExpanded }));
    };

    const isSelected = selectedSpan?.span_id === span.span_id;

    // Get color theme based on span type
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
          onClick={() => setSelectedSpan(span)}
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
          {/* Collapse/Expand button */}
          <div style={{ width: "20px", display: "flex", justifyContent: "center" }}>
            {hasChildren && (
              <span onClick={toggleExpand} style={{ display: "inline-flex", cursor: "pointer" }}>
                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </span>
            )}
          </div>

          {/* Span type Indicator */}
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

          {/* Name */}
          <span style={{ fontWeight: 500, fontSize: "13px", color: isSelected ? "var(--text-primary)" : "#d1d5db", flexGrow: 1 }}>
            {span.name} {span.model && <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 400 }}>({span.model})</span>}
          </span>

          {/* Duration */}
          <span style={{ fontSize: "11px", color: "var(--text-secondary)", marginLeft: "12px" }}>
            {formatDuration(span.duration_ms)}
          </span>

          {/* Status Dot */}
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
              <SpanNode key={child.span_id} span={child} allSpans={allSpans} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  };

  // Render Span Tree Visualizer
  const renderSpanTree = (spans: Span[]) => {
    if (!spans || spans.length === 0) return <div style={{ color: "var(--text-secondary)", padding: "16px" }}>No spans recorded for this run.</div>;

    // Resolve roots (spans with no parent or whose parent is not in the spans list)
    const spanIds = spans.map(s => s.span_id);
    const roots = spans.filter(s => !s.parent_span_id || !spanIds.includes(s.parent_span_id));

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
        {roots.map(root => (
          <SpanNode key={root.span_id} span={root} allSpans={spans} depth={0} />
        ))}
      </div>
    );
  };

  // Recharts metric calculations
  const chartData = useMemo(() => {
    // Collect last 10 runs to show chart
    const items = [...runs].reverse().slice(-15);
    return items.map((r, idx) => ({
      name: r.name.length > 15 ? `${r.name.slice(0, 15)}...` : r.name,
      latency: r.duration_ms || 0,
      cost: Number(r.total_cost_usd || 0) * 1000, // micro-dollars
      tokens: r.total_tokens || 0
    }));
  }, [runs]);

  return (
    <div className="dashboard-container">
      {/* Sidebar Navigation */}
      <div className="sidebar">
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "36px" }}>
          <div style={{ backgroundColor: "var(--primary)", width: "32px", height: "32px", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Activity size={18} color="#fff" />
          </div>
          <span style={{ fontSize: "20px", fontWeight: 700, fontFamily: "var(--font-display)", letterSpacing: "-0.5px" }}>
            AgentWatch <span style={{ color: "var(--primary)", fontSize: "11px", fontWeight: 500, verticalAlign: "super" }}>MVP</span>
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "8px", flexGrow: 1 }}>
          <button 
            onClick={() => { setActiveTab("runs"); setSelectedRunId(null); }}
            className={`glass-panel ${activeTab === "runs" ? "active" : ""}`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "12px 16px",
              borderRadius: "var(--radius-md)",
              color: activeTab === "runs" ? "var(--text-primary)" : "var(--text-secondary)",
              background: activeTab === "runs" ? "rgba(139, 92, 246, 0.15)" : "transparent",
              borderColor: activeTab === "runs" ? "rgba(139, 92, 246, 0.25)" : "transparent",
              textAlign: "left"
            }}
          >
            <List size={18} />
            <span style={{ fontWeight: 500 }}>Live Agent Runs</span>
          </button>

          <button 
            onClick={() => { setActiveTab("metrics"); setSelectedRunId(null); }}
            className={`glass-panel ${activeTab === "metrics" ? "active" : ""}`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "12px 16px",
              borderRadius: "var(--radius-md)",
              color: activeTab === "metrics" ? "var(--text-primary)" : "var(--text-secondary)",
              background: activeTab === "metrics" ? "rgba(139, 92, 246, 0.15)" : "transparent",
              borderColor: activeTab === "metrics" ? "rgba(139, 92, 246, 0.25)" : "transparent",
              textAlign: "left"
            }}
          >
            <BarChart3 size={18} />
            <span style={{ fontWeight: 500 }}>Performance Charts</span>
          </button>

          <button 
            onClick={() => { setActiveTab("settings"); setSelectedRunId(null); }}
            className={`glass-panel ${activeTab === "settings" ? "active" : ""}`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "12px 16px",
              borderRadius: "var(--radius-md)",
              color: activeTab === "settings" ? "var(--text-primary)" : "var(--text-secondary)",
              background: activeTab === "settings" ? "rgba(139, 92, 246, 0.15)" : "transparent",
              borderColor: activeTab === "settings" ? "rgba(139, 92, 246, 0.25)" : "transparent",
              textAlign: "left"
            }}
          >
            <Settings size={18} />
            <span style={{ fontWeight: 500 }}>Settings & OTel</span>
          </button>
        </div>

        {/* Footer */}
        <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px", color: "var(--text-muted)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--status-success)" }}></div>
            <span>Connected: localhost:8000</span>
          </div>
          <span>MIT License | v1.0.0</span>
        </div>
      </div>

      {/* Main View Area */}
      <div className="main-content">
        
        {/* TABS */}

        {/* Runs Tab */}
        {activeTab === "runs" && !selectedRunId && (
          <div>
            <div className="header">
              <div>
                <h1 style={{ fontSize: "28px", fontWeight: 700 }}>Agent Runs</h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginTop: "4px" }}>Monitor runs cost, latency, and spans structure in real-time.</p>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                {/* Search Bar */}
                <div 
                  className="glass-panel"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "8px 14px",
                    borderRadius: "var(--radius-md)",
                    width: "280px"
                  }}
                >
                  <Search size={16} color="var(--text-secondary)" style={{ marginRight: "10px" }} />
                  <input 
                    type="text" 
                    placeholder="Search by name, tags..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{ fontSize: "13px", width: "100%" }}
                  />
                </div>

                {/* Refresh Trigger */}
                <button 
                  onClick={fetchRuns}
                  className="glass-panel"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "36px",
                    height: "36px",
                    borderRadius: "var(--radius-md)"
                  }}
                >
                  <RefreshCw size={16} className={loading ? "spin" : ""} />
                </button>
              </div>
            </div>

            {/* Error notifications */}
            {error && (
              <div 
                style={{
                  backgroundColor: "var(--status-error-bg)",
                  color: "var(--status-error)",
                  border: "1px solid rgba(244, 63, 94, 0.2)",
                  padding: "16px",
                  borderRadius: "var(--radius-md)",
                  marginBottom: "24px",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px"
                }}
              >
                <AlertCircle size={18} />
                <span>{error}</span>
              </div>
            )}

            {/* Stats Cards Grid */}
            <div className="stats-grid">
              <div className="stat-card glass-panel info">
                <span className="stat-label">Total Runs</span>
                <span className="stat-value">{stats.totalRuns}</span>
              </div>
              <div className="stat-card glass-panel success">
                <span className="stat-label">Avg Latency (Success)</span>
                <span className="stat-value">{formatDuration(stats.avgLatency)}</span>
              </div>
              <div className="stat-card glass-panel error">
                <span className="stat-label">Errors</span>
                <span className="stat-value">{stats.errorRuns}</span>
              </div>
              <div className="stat-card glass-panel">
                <span className="stat-label">Total Spans Logged</span>
                <span className="stat-value">{stats.totalSpans}</span>
              </div>
              <div className="stat-card glass-panel">
                <span className="stat-label">Accrued cost</span>
                <span className="stat-value" style={{ color: "#a78bfa" }}>{formatCost(stats.totalCost)}</span>
              </div>
            </div>

            {/* Runs Table Grid */}
            <div className="glass-panel" style={{ padding: "16px", overflow: "hidden" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 10px 16px 10px" }}>
                <span style={{ fontWeight: 600, fontSize: "16px" }}>Latest Ingested Chains</span>
                <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Updated live via WebSocket</span>
              </div>
              
              {loading && runs.length === 0 ? (
                <div style={{ textAlign: "center", padding: "40px", color: "var(--text-secondary)" }}>Loading runs pipeline...</div>
              ) : filteredRuns.length === 0 ? (
                <div style={{ textAlign: "center", padding: "40px", color: "var(--text-secondary)" }}>No runs match current query filter.</div>
              ) : (
                <div className="runs-table-wrapper">
                  <table className="runs-table">
                    <thead>
                      <tr>
                        <th>Run Name</th>
                        <th>Status</th>
                        <th>Session ID</th>
                        <th>Tags</th>
                        <th>Duration</th>
                        <th>Total Tokens</th>
                        <th>Cost</th>
                        <th>Time Started</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRuns.map((run) => (
                        <tr key={run.run_id} onClick={() => setSelectedRunId(run.run_id)}>
                          <td style={{ fontWeight: 600 }}>{run.name}</td>
                          <td>
                            <span className={`badge ${run.status}`}>
                              {run.status}
                            </span>
                          </td>
                          <td style={{ color: run.session_id ? "var(--text-primary)" : "var(--text-muted)" }}>
                            {run.session_id || "N/A"}
                          </td>
                          <td>
                            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                              {formatTags(run.tags).map((tag, idx) => (
                                <span key={idx} style={{ fontSize: "11px", backgroundColor: "rgba(255,255,255,0.06)", padding: "2px 6px", borderRadius: "4px" }}>
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td style={{ fontFamily: "monospace" }}>{formatDuration(run.duration_ms)}</td>
                          <td>{run.total_tokens || 0}</td>
                          <td style={{ color: "#a78bfa", fontWeight: 500 }}>{formatCost(run.total_cost_usd)}</td>
                          <td style={{ color: "var(--text-secondary)", fontSize: "12px" }}>
                            {new Date(run.started_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Selected Run Details / Inspector Split View */}
        {selectedRunId && (
          <div>
            {/* Header / Breadcrumb */}
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "20px" }}>
              <button 
                onClick={() => setSelectedRunId(null)}
                style={{ color: "var(--text-secondary)", fontSize: "14px", display: "flex", alignItems: "center", gap: "4px", cursor: "pointer" }}
              >
                <ChevronRight size={16} style={{ transform: "rotate(180deg)" }} />
                <span>Back to Runs</span>
              </button>
              <span style={{ color: "var(--text-muted)" }}>/</span>
              <span style={{ fontWeight: 600 }}>{selectedRunDetails?.name || "Inspect Trace"}</span>
            </div>

            {!selectedRunDetails ? (
              <div className="glass-panel" style={{ padding: "40px", textAlign: "center" }}>Fetching run hierarchy and traces details...</div>
            ) : (
              <div style={{ display: "flex", gap: "24px", alignItems: "stretch" }}>
                
                {/* Left Side: Span Waterfall Tree Layout */}
                <div className="glass-panel" style={{ width: "45%", padding: "24px", display: "flex", flexDirection: "column" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", paddingBottom: "16px", borderBottom: "1px solid var(--border-color)", marginBottom: "16px" }}>
                    <Layers size={18} color="var(--primary)" />
                    <h3 style={{ fontSize: "16px", fontWeight: 600 }}>Trace Waterfall Cascade</h3>
                  </div>

                  <div style={{ flexGrow: 1, overflowY: "auto", maxH: "65vh" }}>
                    {renderSpanTree(selectedRunDetails.spans || [])}
                  </div>
                </div>

                {/* Right Side: Selected Span Details Inspector */}
                <div className="glass-panel" style={{ width: "55%", padding: "24px", display: "flex", flexDirection: "column" }}>
                  {selectedSpan ? (
                    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
                      
                      {/* Name / Header */}
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

                      {/* Stat Metrics Box */}
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

                      {/* Input/Output Previews */}
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

                        {/* Raw metadata JSON */}
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
                  ) : (
                    <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)" }}>
                      Select a span from the left cascade tree to inspect parameters and outputs.
                    </div>
                  )}
                </div>

              </div>
            )}
          </div>
        )}

        {/* Metrics Overview Tab */}
        {activeTab === "metrics" && (
          <div>
            <div className="header">
              <div>
                <h1 style={{ fontSize: "28px", fontWeight: 700 }}>Performance Metrics</h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginTop: "4px" }}>Analyze your LLM latency distributions and costs.</p>
              </div>
            </div>

            {runs.length === 0 ? (
              <div className="glass-panel" style={{ padding: "40px", textAlign: "center", color: "var(--text-secondary)" }}>
                No active runs recorded to generate chart parameters. Connect your SDK to start plotting metrics.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                
                {/* Latency Area Chart */}
                <div className="glass-panel" style={{ padding: "24px" }}>
                  <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>Successful Run Latency (ms)</h3>
                  <div style={{ width: "100%", height: 300 }}>
                    <ResponsiveContainer>
                      <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorLatency" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="var(--secondary)" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="var(--secondary)" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={11} />
                        <YAxis stroke="var(--text-muted)" fontSize={11} unit="ms" />
                        <Tooltip contentStyle={{ backgroundColor: "var(--bg-secondary)", borderColor: "var(--border-color)", color: "var(--text-primary)" }} />
                        <Area type="monotone" dataKey="latency" stroke="var(--secondary)" fillOpacity={1} fill="url(#colorLatency)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Costs Area Chart */}
                <div className="glass-panel" style={{ padding: "24px" }}>
                  <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>Token Consumption Costs (Micro-USD)</h3>
                  <div style={{ width: "100%", height: 300 }}>
                    <ResponsiveContainer>
                      <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={11} />
                        <YAxis stroke="var(--text-muted)" fontSize={11} unit="μ$" />
                        <Tooltip contentStyle={{ backgroundColor: "var(--bg-secondary)", borderColor: "var(--border-color)", color: "var(--text-primary)" }} />
                        <Area type="monotone" dataKey="cost" stroke="var(--primary)" fillOpacity={1} fill="url(#colorCost)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

              </div>
            )}
          </div>
        )}

        {/* Settings / OpenTelemetry Setup Tab */}
        {activeTab === "settings" && (
          <div>
            <div className="header">
              <div>
                <h1 style={{ fontSize: "28px", fontWeight: 700 }}>Settings & Integration</h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginTop: "4px" }}>Configure SDK connections and inspect OpenTelemetry endpoints.</p>
              </div>
            </div>

            <div style={{ display: "flex", gap: "24px" }}>
              
              {/* Left Side: Server Configuration Form */}
              <div className="glass-panel" style={{ width: "50%", padding: "24px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
                  <Database size={18} color="var(--primary)" />
                  Backend Connection Config
                </h3>
                
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div>
                    <label style={{ fontSize: "13px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>AgentWatch Server URL</label>
                    <input 
                      type="text" 
                      value={backendUrl}
                      onChange={(e) => setBackendUrl(e.target.value)}
                      style={{ width: "100%", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--border-color)", backgroundColor: "rgba(0,0,0,0.2)" }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: "13px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>AGENTWATCH_API_KEY (Optional Auth Key)</label>
                    <input 
                      type="password" 
                      value={apiKey}
                      placeholder="••••••••••••"
                      onChange={(e) => setApiKey(e.target.value)}
                      style={{ width: "100%", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--border-color)", backgroundColor: "rgba(0,0,0,0.2)" }}
                    />
                  </div>

                  <button 
                    onClick={() => saveConfig(backendUrl, apiKey)}
                    style={{ backgroundColor: "var(--primary)", color: "#fff", padding: "12px", borderRadius: "8px", fontWeight: 600, cursor: "pointer", transition: "var(--transition)", textAlign: "center" }}
                  >
                    Save Server Configuration
                  </button>
                </div>
              </div>

              {/* Right Side: OpenTelemetry Setup Guide */}
              <div className="glass-panel" style={{ width: "50%", padding: "24px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
                  <Terminal size={18} color="var(--secondary)" />
                  OTel OTLP Ingest Integration
                </h3>

                <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "16px" }}>
                  AgentWatch accepts standard OpenTelemetry traces natively. You can target the OTLP/HTTP exporter endpoint directly in your existing application instrumentation pipelines.
                </p>

                <div style={{ backgroundColor: "rgba(0,0,0,0.3)", border: "1px solid var(--border-color)", padding: "16px", borderRadius: "8px" }}>
                  <span style={{ fontSize: "12px", color: "var(--text-secondary)", textTransform: "uppercase", fontWeight: 600, display: "block", marginBottom: "8px" }}>OTLP HTTP Target Endpoint</span>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <code style={{ fontSize: "13px", fontFamily: "monospace", color: "var(--primary)" }}>
                      {backendUrl}/v1/traces
                    </code>
                    <button 
                      onClick={() => navigator.clipboard.writeText(`${backendUrl}/v1/traces`)}
                      style={{ cursor: "pointer", opacity: 0.7, hover: { opacity: 1 } }}
                    >
                      <Copy size={16} />
                    </button>
                  </div>
                </div>

                <div style={{ marginTop: "20px" }}>
                  <span style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px" }}>Quick environment export:</span>
                  <pre style={{ backgroundColor: "rgba(0,0,0,0.2)", padding: "12px", borderRadius: "6px", fontSize: "12px", fontFamily: "monospace" }}>
                    export OTEL_EXPORTER_OTLP_ENDPOINT="{backendUrl}/v1/traces"<br />
                    export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
                  </pre>
                </div>
              </div>

            </div>
          </div>
        )}

      </div>
    </div>
  );
}
