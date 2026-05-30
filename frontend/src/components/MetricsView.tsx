interface ChartDataPoint {
  name: string;
  latency: number;
  cost: number;
  tokens: number;
}

interface MetricsViewProps {
  chartData: ChartDataPoint[];
}

function BarChart({ data, dataKey, color, label, unit }: {
  data: ChartDataPoint[];
  dataKey: "latency" | "cost" | "tokens";
  color: string;
  label: string;
  unit: string;
}) {
  const maxVal = Math.max(...data.map(d => d[dataKey]), 1);

  return (
    <div className="glass-panel" style={{ padding: "24px" }}>
      <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>{label}</h3>
      <div style={{ width: "100%", height: 300, display: "flex", alignItems: "flex-end", gap: "8px", paddingTop: "20px" }}>
        {data.map((d, i) => {
          const val = d[dataKey];
          const pct = (val / maxVal) * 100;
          return (
            <div
              key={i}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                height: "100%",
                justifyContent: "flex-end",
              }}
              title={`${d.name}: ${val}${unit}`}
            >
              <div
                style={{
                  width: "100%",
                  maxWidth: 48,
                  height: `${Math.max(pct, 2)}%`,
                  backgroundColor: color,
                  borderRadius: "4px 4px 0 0",
                  transition: "height 0.3s ease",
                  opacity: 0.85,
                  cursor: "pointer",
                }}
                className="chart-bar"
              />
              <span style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 6, writingMode: "vertical-lr", textOrientation: "mixed", height: 40, overflow: "hidden", textOverflow: "ellipsis" }}>
                {d.name}
              </span>
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 4px 0", fontSize: 11, color: "var(--text-muted)" }}>
        <span>Max: {maxVal}{unit}</span>
        <span>Total: {data.reduce((s, d) => s + d[dataKey], 0)}{unit}</span>
      </div>
    </div>
  );
}

export function MetricsView({ chartData }: MetricsViewProps) {
  return (
    <div>
      <div className="header">
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 700 }}>Performance Metrics</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginTop: "4px" }}>Analyze your LLM latency distributions and costs.</p>
        </div>
      </div>

      {chartData.length === 0 ? (
        <div className="glass-panel" style={{ padding: "40px", textAlign: "center", color: "var(--text-secondary)" }}>
          No active runs recorded to generate chart parameters. Connect your SDK to start plotting metrics.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <BarChart
            data={chartData}
            dataKey="latency"
            color="var(--secondary)"
            label="Successful Run Latency (ms)"
            unit="ms"
          />
          <BarChart
            data={chartData}
            dataKey="cost"
            color="var(--primary)"
            label="Token Consumption Costs (Micro-USD)"
            unit="μ$"
          />
        </div>
      )}

      <style>{`
        .chart-bar:hover {
          opacity: 1 !important;
          transform: scaleX(1.05);
        }
      `}</style>
    </div>
  );
}
