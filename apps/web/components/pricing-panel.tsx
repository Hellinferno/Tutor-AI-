"use client";

import { useEffect, useState } from "react";
import { ApiError, getUsageSummary, listPlans, subscribe } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { Plan, PlanTier, UsageSummary } from "../lib/types";

export function PricingPanel() {
  const { userId } = useNotebook();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function refresh() {
    try {
      const [p, u] = await Promise.all([listPlans(), getUsageSummary(userId)]);
      setPlans(p.plans);
      setUsage(u);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load billing.");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  async function choose(tier: PlanTier) {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const result = await subscribe(userId, tier);
      setNote(result.checkout.message);
      if (result.checkout.checkout_url) window.open(result.checkout.checkout_url, "_blank");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Subscription change failed.");
    } finally {
      setBusy(false);
    }
  }

  function price(p: Plan) {
    return p.price_cents === 0 ? "Free" : `$${(p.price_cents / 100).toFixed(2)}/mo`;
  }

  return (
    <section className="panel wide" id="pricing">
      <div className="panelHeader">
        <h3>Plans &amp; usage</h3>
        <span className="badge">{usage ? `${usage.tier} · ${usage.provider}` : "Phase 4"}</span>
      </div>

      <div className="planGrid">
        {plans.map((p) => {
          const current = usage?.tier === p.tier;
          return (
            <div className={current ? "planCard current" : "planCard"} key={p.tier}>
              <strong className="planName">{p.name}</strong>
              <span className="planPrice">{price(p)}</span>
              <ul className="planFeatures">
                {p.features.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
              <button type="button" className="submitBtn" onClick={() => choose(p.tier)} disabled={busy || current}>
                {current ? "Current plan" : `Switch to ${p.name}`}
              </button>
            </div>
          );
        })}
      </div>

      {note && <small className="muted13">{note}</small>}
      {error && <small className="errorText">{error}</small>}

      {usage && (
        <div className="usageBox">
          <p className="muted13">
            Usage this period ({usage.billing_period}) — status: <strong>{usage.status}</strong>
          </p>
          <div className="usageGrid">
            {usage.actions.map((a) => (
              <div className="usageRow" key={a.action}>
                <span>{a.action}</span>
                <span className={a.allowed ? "" : "weakTag"}>
                  {a.used}
                  {a.limit === null ? " / ∞" : ` / ${a.limit}`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
