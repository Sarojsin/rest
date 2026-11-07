import { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminDiagnosticsPage() {
  const { admin, has, loading: authLoading, error: authError } = usePlatformAuth();
  const [status, setStatus] = useState<string | null>(null);
  const [systemInfo, setSystemInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDiagnostics() {
      setLoading(true);
      setError(null);
      try {
        const res: Response = await platformFetch("/api/platform/diagnostics/health");
        const data = await res.json();
        setStatus(data.status || "unknown");
        setSystemInfo(data);
      } catch (err: any) {
        setError(err.detail || "Failed to load diagnostics.");
      } finally {
        setLoading(false);
      }
    }

    // Load if admin is available
    if (admin) {
      loadDiagnostics();
    } else if (authLoading === false) {
      // Try loading even without full admin auth
      loadDiagnostics();
    }
  }, [admin]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ marginTop: 0 }}>Diagnostics</h1>
        <p>Loading diagnostics…</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
      <h1 style={{ marginTop: 0 }}>Diagnostics</h1>
      {error ? <div className="pf-error">{error}</div> : null}

      {status ? (
        <div style={{ marginBottom: 16 }}>
          <strong>Status:</strong> {status}
        </div>
      ) : null}

      {systemInfo ? (
        <pre style={{ background: "#f1f5f9", padding: 16, borderRadius: 8, fontSize: 12, overflowX: "auto" }}>
          {JSON.stringify(systemInfo, null, 2)}
        </pre>
      ) : null}

      <div style={{ marginTop: 32 }}>
        <button className="pf-button" onClick={() => window.history.back()}>
          Go Back
        </button>
      </div>
    </div>
  );
}