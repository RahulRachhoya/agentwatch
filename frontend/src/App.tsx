import { useState, useEffect, useMemo } from "react";
import { Activity, Settings, BarChart3, List } from "lucide-react";
import { useWebSocket } from "./hooks/useWebSocket";
import { RunsListView, type Run } from "./components/RunsListView";
import { RunDetailsView } from "./components/RunDetailsView";
import { SettingsView } from "./components/SettingsView";
import type { Span } from "./components/SpanTree";
import { MetricsView } from "./components/MetricsView";

export default function App() {
  const [activeTab, setActiveTab] = useState<"runs" | "metrics" | "settings">("runs");

  const [backendUrl, setBackendUrl] = useState(() => {
    return localStorage.getItem("aw_backend_url") || "http://localhost:8000";
  });
  const [apiKey, setApiKey] = useState(() => {
    return localStorage.getItem("aw_api_key") || "";
  });

  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRunDetails, setSelectedRunDetails] = useState<Run | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSpans, setExpandedSpans] = useState<Record<string, boolean>>({});

  const saveConfig = (url: string, key: string) => {
    localStorage.setItem("aw_backend_url", url);
    localStorage.setItem("aw_api_key", key);
    setBackendUrl(url);
    setApiKey(key);
    fetchRuns();
  };

  const getHeaders = () => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json"
    };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }
    return headers;
  };

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

  const fetchRunDetails = async (runId: string) => {
    try {
      const res = await fetch(`${backendUrl}/v1/runs/${runId}`, {
        headers: getHeaders()
      });
      if (res.ok) {
        const json = await res.json();
        const runData = json.data;
        setSelectedRunDetails(runData);
        if (runData.spans && runData.spans.length > 0) {
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

  useEffect(() => {
    fetchRuns();
  }, [backendUrl, apiKey]);

  useEffect(() => {
    if (selectedRunId) {
      fetchRunDetails(selectedRunId);
    } else {
      setSelectedRunDetails(null);
      setSelectedSpan(null);
    }
  }, [selectedRunId]);

  useWebSocket(backendUrl, (msg) => {
    console.log("WebSocket event received:", msg);
    const { type, data } = msg;

    if (type === "run_started") {
      setRuns((prev) => {
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
      if (selectedRunId === data.run_id) {
        fetchRunDetails(data.run_id);
      }
      fetchRuns();
    }
  });

  const stats = useMemo(() => {
    const totalRuns = runs.length;
    const completedRuns = runs.filter(r => r.status === "success");
    const errorRuns = runs.filter(r => r.status === "error");
    const totalCost = runs.reduce((acc, r) => acc + Number(r.total_cost_usd || 0), 0);
    const totalSpans = runs.reduce((acc, r) => acc + (r.span_count || 0), 0);

    const successfulDurations = completedRuns.filter(r => r.duration_ms).map(r => r.duration_ms as number);
    const avgLatency = successfulDurations.length
      ? Math.round(successfulDurations.reduce((acc, val) => acc + val, 0) / successfulDurations.length)
      : 0;

    return { totalRuns, errorRuns: errorRuns.length, totalCost, totalSpans, avgLatency };
  }, [runs]);

  const filteredRuns = useMemo(() => {
    if (!searchQuery) return runs;

    return runs.filter(run => {
      const nameMatch = run.name.toLowerCase().includes(searchQuery.toLowerCase());
      const sessionMatch = run.session_id?.toLowerCase().includes(searchQuery.toLowerCase());

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

  const formatTags = (tags: any): string[] => {
    if (!tags) return [];
    if (Array.isArray(tags)) return tags;
    try {
      const parsed = JSON.parse(tags.replace(/'/g, '"'));
      if (Array.isArray(parsed)) return parsed;
    } catch (_) {}
    return typeof tags === "string" ? tags.split(",").map(t => t.trim()).filter(Boolean) : [];
  };

  const formatCost = (cost: number) => {
    if (cost === 0) return "$0.000000";
    return `$${cost.toFixed(6)}`;
  };

  const formatDuration = (ms: number | null) => {
    if (ms === null) return "Running";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const handleToggleExpand = (spanId: string) => {
    setExpandedSpans(prev => ({ ...prev, [spanId]: !prev[spanId] }));
  };

  const chartData = useMemo(() => {
    const items = [...runs].reverse().slice(-15);
    return items.map((r) => ({
      name: r.name.length > 15 ? `${r.name.slice(0, 15)}...` : r.name,
      latency: r.duration_ms || 0,
      cost: Number(r.total_cost_usd || 0) * 1000,
      tokens: r.total_tokens || 0
    }));
  }, [runs]);

  return (
    <div className="dashboard-container">
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

        <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px", color: "var(--text-muted)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--status-success)" }}></div>
            <span>Connected: localhost:8000</span>
          </div>
          <span>MIT License | v1.0.0</span>
        </div>
      </div>

      <div className="main-content">
        {activeTab === "runs" && !selectedRunId && (
          <RunsListView
            runs={filteredRuns}
            searchQuery={searchQuery}
            loading={loading}
            error={error}
            stats={stats}
            onSearchChange={setSearchQuery}
            onRefresh={fetchRuns}
            onSelectRun={setSelectedRunId}
            formatDuration={formatDuration}
            formatCost={formatCost}
            formatTags={formatTags}
          />
        )}

        {selectedRunId && selectedRunDetails && (
          <RunDetailsView
            runName={selectedRunDetails.name}
            spans={selectedRunDetails.spans || []}
            selectedSpan={selectedSpan}
            expandedSpans={expandedSpans}
            onBack={() => setSelectedRunId(null)}
            onToggleExpand={handleToggleExpand}
            onSelectSpan={setSelectedSpan}
            formatDuration={formatDuration}
            formatCost={formatCost}
          />
        )}

        {selectedRunId && !selectedRunDetails && (
          <div className="glass-panel" style={{ padding: "40px", textAlign: "center" }}>
            Fetching run hierarchy and traces details...
          </div>
        )}

        {activeTab === "metrics" && (
          <MetricsView chartData={chartData} />
        )}

        {activeTab === "settings" && (
          <SettingsView
            backendUrl={backendUrl}
            apiKey={apiKey}
            onBackendUrlChange={setBackendUrl}
            onApiKeyChange={setApiKey}
            onSave={() => saveConfig(backendUrl, apiKey)}
          />
        )}
      </div>
    </div>
  );
}
