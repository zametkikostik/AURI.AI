"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function headers(): HeadersInit {
  const t = typeof window !== "undefined" ? localStorage.getItem("auri_access_token") : null;
  return t
    ? { Authorization: `Bearer ${t}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}

type Usage = {
  plan: string;
  meetings: { used: number; limit: number | null };
  hours: { used: number; limit: number | null };
  members: { used: number; limit: number | null };
  features: { team: boolean; sso: boolean };
};

export default function BillingPage() {
  const [usage, setUsage] = useState<Usage | null>(null);
  const [stripeOn, setStripeOn] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setErr(null);
    try {
      const [u, s] = await Promise.all([
        fetch(`${API}/api/v1/billing/usage`, { headers: headers() }),
        fetch(`${API}/api/v1/billing/stripe/status`, { headers: headers() }),
      ]);
      if (!u.ok) throw new Error(`Usage ${u.status}`);
      setUsage(await u.json());
      if (s.ok) {
        const j = await s.json();
        setStripeOn(!!j.configured);
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function upgrade() {
    setLoading(true);
    setMsg(null);
    setErr(null);
    try {
      const res = await fetch(`${API}/api/v1/billing/upgrade`, {
        method: "POST",
        headers: headers(),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
        return;
      }
      setMsg(data.message || "Upgraded");
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Upgrade failed");
    } finally {
      setLoading(false);
    }
  }

  async function openPortal() {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetch(`${API}/api/v1/billing/portal`, {
        method: "POST",
        headers: headers(),
      });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
        return;
      }
      setErr(data.error || "Portal unavailable");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Portal failed");
    } finally {
      setLoading(false);
    }
  }

  const isEnterprise = usage?.plan === "enterprise";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
        <p className="mt-1 text-sm text-muted-foreground">Plan usage and upgrades</p>
      </div>

      {err && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{err}</div>
      )}
      {msg && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{msg}</div>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card label="Plan" value={usage?.plan ?? "—"} />
        <Card
          label="Meetings"
          value={
            usage
              ? `${usage.meetings.used}${usage.meetings.limit != null ? ` / ${usage.meetings.limit}` : ""}`
              : "—"
          }
        />
        <Card
          label="Hours"
          value={
            usage
              ? `${usage.hours.used}${usage.hours.limit != null ? ` / ${usage.hours.limit}` : ""}`
              : "—"
          }
        />
      </div>

      <section className="space-y-4 rounded-lg border p-5">
        <h2 className="font-medium">Enterprise</h2>
        <ul className="list-inside list-disc text-sm text-muted-foreground">
          <li>Unlimited meetings and transcription hours</li>
          <li>SSO (Google / Microsoft / Okta)</li>
          <li>Team features and audit logs</li>
        </ul>
        <div className="flex flex-wrap gap-2">
          {!isEnterprise && (
            <button
              type="button"
              disabled={loading}
              onClick={upgrade}
              className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
            >
              {loading ? "Please wait…" : stripeOn ? "Upgrade with Stripe" : "Upgrade (dev)"}
            </button>
          )}
          {isEnterprise && (
            <button
              type="button"
              disabled={loading}
              onClick={openPortal}
              className="rounded-lg border px-5 py-2.5 text-sm font-medium hover:bg-secondary disabled:opacity-50"
            >
              Manage subscription / invoices
            </button>
          )}
          <Link href="/settings" className="rounded-lg border px-5 py-2.5 text-sm hover:bg-secondary">
            Settings
          </Link>
        </div>
        <p className="text-xs text-muted-foreground">
          Stripe: {stripeOn ? "configured" : "not configured (dev fallback)"}
        </p>
      </section>
    </div>
  );
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-xl font-semibold capitalize">{value}</div>
    </div>
  );
}
