import { Database, Terminal, Copy } from "lucide-react";

interface SettingsViewProps {
  backendUrl: string;
  apiKey: string;
  onBackendUrlChange: (url: string) => void;
  onApiKeyChange: (key: string) => void;
  onSave: () => void;
}

export function SettingsView({
  backendUrl,
  apiKey,
  onBackendUrlChange,
  onApiKeyChange,
  onSave
}: SettingsViewProps) {
  return (
    <div>
      <div className="header">
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 700 }}>Settings & Integration</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginTop: "4px" }}>Configure SDK connections and inspect OpenTelemetry endpoints.</p>
        </div>
      </div>

      <div style={{ display: "flex", gap: "24px" }}>
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
                onChange={(e) => onBackendUrlChange(e.target.value)}
                style={{ width: "100%", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--border-color)", backgroundColor: "rgba(0,0,0,0.2)" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "13px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>AGENTWATCH_API_KEY (Optional Auth Key)</label>
              <input
                type="password"
                value={apiKey}
                placeholder="••••••••••••"
                onChange={(e) => onApiKeyChange(e.target.value)}
                style={{ width: "100%", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--border-color)", backgroundColor: "rgba(0,0,0,0.2)" }}
              />
            </div>

            <button
              onClick={onSave}
              style={{ backgroundColor: "var(--primary)", color: "#fff", padding: "12px", borderRadius: "8px", fontWeight: 600, cursor: "pointer", transition: "var(--transition)", textAlign: "center" }}
            >
              Save Server Configuration
            </button>
          </div>
        </div>

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
                className="copy-button"
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
  );
}
