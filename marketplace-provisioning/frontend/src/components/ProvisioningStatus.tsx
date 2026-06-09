import { useState, useEffect } from "react";

interface ProvisioningEvent {
  step: string;
  message: string;
  progress: number;
  total: number;
  genie_url?: string;
  error?: boolean;
}

const STEP_LABELS: Record<string, string> = {
  pending: "Preparing your investigation...",
  auth: "Connecting to workspace...",
  warehouse: "Finding SQL warehouse...",
  catalog: "Setting up the evidence locker...",
  upload: "Loading the evidence files...",
  tables: "Cataloging the evidence...",
  grants: "Securing access...",
  genie: "Opening the investigation room...",
  done: "Your case is ready!",
  error: "Something went wrong",
};

interface Props {
  accountId: string;
  onComplete: (genieUrl: string) => void;
}

export default function ProvisioningStatus({ accountId, onComplete }: Props) {
  const [event, setEvent] = useState<ProvisioningEvent>({
    step: "pending",
    message: "Preparing your investigation...",
    progress: 0,
    total: 8,
  });
  const [usePolling, setUsePolling] = useState(false);

  // Try SSE first, fall back to polling
  useEffect(() => {
    if (usePolling) return;

    let cancelled = false;
    const evtSource = new EventSource(`/api/provisioning/${accountId}/status`);

    evtSource.onmessage = (e) => {
      if (cancelled) return;
      try {
        const data: ProvisioningEvent = JSON.parse(e.data);
        setEvent(data);
        if (data.step === "done" && data.genie_url) {
          evtSource.close();
          onComplete(data.genie_url);
        }
      } catch {}
    };

    evtSource.onerror = () => {
      if (!cancelled) {
        evtSource.close();
        setUsePolling(true);
      }
    };

    return () => {
      cancelled = true;
      evtSource.close();
    };
  }, [accountId, usePolling, onComplete]);

  // Polling fallback
  useEffect(() => {
    if (!usePolling) return;
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch(`/api/provisioning/${accountId}/poll`);
        if (!res.ok) return;
        const data: ProvisioningEvent = await res.json();
        if (!cancelled) {
          setEvent(data);
          if (data.step === "done" && data.genie_url) {
            onComplete(data.genie_url);
          }
        }
      } catch {}
    }

    poll();
    const id = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [accountId, usePolling, onComplete]);

  const progressPct = event.total > 0 ? (event.progress / event.total) * 100 : 0;

  return (
    <div className="card text-center" style={{ marginTop: "12vh" }}>
      <p className="divider" style={{ marginBottom: 12 }}>&#9830; &#9830; &#9830;</p>
      <h1>Preparing Your Case</h1>

      {event.error ? (
        <div style={{ marginTop: 24 }}>
          <p className="text-error" style={{ fontSize: "1.05rem", marginBottom: 16 }}>
            {event.message}
          </p>
          <button
            className="btn-primary"
            onClick={() => window.location.reload()}
          >
            Try Again
          </button>
        </div>
      ) : (
        <>
          {/* Progress bar */}
          <div
            style={{
              marginTop: 24,
              marginBottom: 16,
              background: "#1e1a30",
              borderRadius: 8,
              height: 8,
              overflow: "hidden",
              border: "1px solid #3a3250",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${progressPct}%`,
                background: "linear-gradient(90deg, #8b1a1a, #d4a853)",
                borderRadius: 8,
                transition: "width 0.5s ease",
              }}
            />
          </div>

          {/* Step indicator */}
          <p style={{ fontSize: "1.05rem", lineHeight: 1.6, marginBottom: 8 }}>
            {STEP_LABELS[event.step] || event.message}
          </p>
          <p className="text-muted" style={{ fontSize: "0.85rem" }}>
            Step {event.progress} of {event.total}
          </p>
          <p className="text-muted" style={{ fontSize: "0.8rem", fontStyle: "italic", marginTop: 8 }}>
            This may take up to a minute. Please don't close this page.
          </p>

          {/* Decorative loading animation */}
          <div
            style={{
              marginTop: 24,
              fontSize: "2rem",
              animation: "pulse 1.5s ease-in-out infinite",
            }}
          >
            <span role="img" aria-label="magnifying glass" style={{ filter: "grayscale(0.3)" }}>
              &#128269;
            </span>
          </div>
        </>
      )}

      <p className="divider" style={{ marginTop: 24 }}>&#9830; &#9830; &#9830;</p>
    </div>
  );
}
