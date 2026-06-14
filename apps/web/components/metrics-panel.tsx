"use client";

import { useEffect, useState } from "react";
import { ApiError, getMetrics } from "../lib/api";
import type { MetricsSnapshot } from "../lib/types";

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function MetricsPanel() {
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      setMetrics(await getMetrics());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load metrics.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <section className="panel" id="metrics">
      <div className="panelHeader">
        <h3>Observability</h3>
        <span className="badge">Phase 5</span>
      </div>

      {error && <small className="errorText">{error}</small>}

      {metrics && (
        <div className="analyticsGrid">
          <div className="analyticsCard">
            <small>Asks</small>
            <span className="bigNumber">{metrics.asks}</span>
            <small>refusal {pct(metrics.weak_retrieval_refusal_rate)}</small>
          </div>
          <div className="analyticsCard">
            <small>Citation coverage</small>
            <span className="bigNumber">{pct(metrics.citation_coverage_rate)}</span>
          </div>
          <div className="analyticsCard">
            <small>Solves</small>
            <span className="bigNumber">{metrics.solves}</span>
            <small>verified {pct(metrics.verified_rate)}</small>
          </div>
          <div className="analyticsCard">
            <small>False‑verified</small>
            <span className="bigNumber">{pct(metrics.false_verified_rate)}</span>
            <small>gate = 0</small>
          </div>
          <div className="analyticsCard">
            <small>Cache hit</small>
            <span className="bigNumber">{pct(metrics.cache_hit_rate)}</span>
          </div>
          <div className="analyticsCard">
            <small>Solve p90</small>
            <span className="bigNumber">{metrics.solve_latency_ms.p90}</span>
            <small>ms</small>
          </div>
        </div>
      )}

      <button type="button" className="secondary" onClick={refresh} disabled={busy}>
        {busy ? "…" : "Refresh metrics"}
      </button>
      <p className="muted13">
        Live counters from <code>GET /metrics</code> — the production observability signals from the spec
        (refusal rate, citation coverage, verified rate, cache hit, solve latency).
      </p>
    </section>
  );
}
