interface StatsCardsProps {
  totalRuns: number;
  avgLatency: number;
  errorRuns: number;
  totalSpans: number;
  totalCost: number;
  formatDuration: (ms: number | null) => string;
  formatCost: (cost: number) => string;
}

export function StatsCards({
  totalRuns,
  avgLatency,
  errorRuns,
  totalSpans,
  totalCost,
  formatDuration,
  formatCost
}: StatsCardsProps) {
  return (
    <div className="stats-grid">
      <div className="stat-card glass-panel info">
        <span className="stat-label">Total Runs</span>
        <span className="stat-value">{totalRuns}</span>
      </div>
      <div className="stat-card glass-panel success">
        <span className="stat-label">Avg Latency (Success)</span>
        <span className="stat-value">{formatDuration(avgLatency)}</span>
      </div>
      <div className="stat-card glass-panel error">
        <span className="stat-label">Errors</span>
        <span className="stat-value">{errorRuns}</span>
      </div>
      <div className="stat-card glass-panel">
        <span className="stat-label">Total Spans Logged</span>
        <span className="stat-value">{totalSpans}</span>
      </div>
      <div className="stat-card glass-panel">
        <span className="stat-label">Accrued cost</span>
        <span className="stat-value" style={{ color: "#a78bfa" }}>{formatCost(totalCost)}</span>
      </div>
    </div>
  );
}
