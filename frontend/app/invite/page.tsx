"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useState, Suspense } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function InviteForm() {
  const params = useSearchParams();
  const router = useRouter();
  const tokenFromUrl = params.get("token") || "";
  const [token, setToken] = useState(tokenFromUrl);
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/v1/members/invites/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          password,
          full_name: fullName || undefined,
        }),
      });
      if (!res.ok) {
        setError(await res.text());
        return;
      }
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6 py-12">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">Accept invitation</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Create your password to join the organization
        </p>
      </div>
      <form onSubmit={onSubmit} className="space-y-4 rounded-xl border bg-card p-6">
        <label className="block space-y-1 text-sm">
          <span className="text-xs text-muted-foreground">Invite token</span>
          <input
            className="w-full rounded-md border px-3 py-2 text-sm"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            required
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-xs text-muted-foreground">Full name</span>
          <input
            className="w-full rounded-md border px-3 py-2 text-sm"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-xs text-muted-foreground">Password</span>
          <input
            type="password"
            className="w-full rounded-md border px-3 py-2 text-sm"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>
        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-primary py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {loading ? "Accepting…" : "Accept invite"}
        </button>
      </form>
    </div>
  );
}

export default function InvitePage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm">Loading…</div>}>
      <InviteForm />
    </Suspense>
  );
}
