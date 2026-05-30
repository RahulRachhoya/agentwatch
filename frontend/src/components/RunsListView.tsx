import { Search, RefreshCw, AlertCircle } from "lucide-react";
import { StatsCards } from "./StatsCards";

export interface Run {
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
  spans?: any[];
}

interface RunsListViewProps {
  runs: Run[];
  searchQuery: string;
  loading: boolean;
  error: string | null;
  stats: {
    totalRuns: number;
    avgLatency: number;
    errorRuns: number;
    totalSpans: number;
    totalCost: number;
  };
  onSearchChange: (query: string) => void;
  onRefresh: () => void;
  onSelectRun: (runId: string) => void;
  formatDuration: (ms: number | null) => string;
  formatCost: (cost: number) => string;
  formatTags: (tags: any) => string[];
}

export function RunsListView({
  runs,
  searchQuery,
  loading,
  error,
  stats,
  onSearchChange,
  onRefresh,
  onSelectRun,
  formatDuration,
  formatCost,
  formatTags
}: RunsListViewProps) {
  return (
    <div>
      <div className="header">
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 700 }}>Agent Runs</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginTop: "4px" }}>Monitor runs cost, latency, and spans structure in real-time.</p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
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
              onChange={(e) => onSearchChange(e.target.value)}
              style={{ fontSize: "13px", width: "100%" }}
            />
          </div>

          <button
            onClick={onRefresh}
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

      <StatsCards
        totalRuns={stats.totalRuns}
        avgLatency={stats.avgLatency}
        errorRuns={stats.errorRuns}
        totalSpans={stats.totalSpans}
        totalCost={stats.totalCost}
        formatDuration={formatDuration}
        formatCost={formatCost}
      />

      <div className="glass-panel" style={{ padding: "16px", overflow: "hidden" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 10px 16px 10px" }}>
          <span style={{ fontWeight: 600, fontSize: "16px" }}>Latest Ingested Chains</span>
          <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Updated live via WebSocket</span>
        </div>

        {loading && runs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px", color: "var(--text-secondary)" }}>Loading runs pipeline...</div>
        ) : runs.length === 0 ? (
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
                {runs.map((run) => (
                  <tr key={run.run_id} onClick={() => onSelectRun(run.run_id)}>
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
  );
}
