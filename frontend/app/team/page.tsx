"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function authHeaders(): HeadersInit {
  const t = localStorage.getItem("auri_access_token");
  return t ? { Authorization: `Bearer ${t}`, "Content-Type": "application/json" } : {};
}

type Member = {
  id: string;
  email: string;
  full_name?: string | null;
  role: string;
  is_active: boolean;
};

type Invite = {
  id: string;
  email: string;
  role: string;
  status: string;
  token: string;
  expires_at: string;
};

export default function TeamPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      const [mRes, iRes] = await Promise.all([
        fetch(`${API}/api/v1/members`, { headers: authHeaders() }),
        fetch(`${API}/api/v1/members/invites`, { headers: authHeaders() }),
      ]);
      if (!mRes.ok) throw new Error(`Members: ${mRes.status}`);
      setMembers(await mRes.json());
      if (iRes.ok) setInvites(await iRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function invite(e: React.FormEvent) {
    e.preventDefault();
    setInfo(null);
    setError(null);
    const res = await fetch(`${API}/api/v1/members/invites`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ email, role }),
    });
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    const inv = (await res.json()) as Invite;
    setInfo(`Invite created. Token (share link): ${inv.token}`);
    setEmail("");
    await load();
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Team</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Members and invitations for your organization
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}
      {info && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 break-all">{info}</div>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Members</h2>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-secondary/50 text-left text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-2">Email</th>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {members.map((m) => (
                <tr key={m.id}>
                  <td className="px-4 py-2">{m.email}</td>
                  <td className="px-4 py-2">{m.full_name || "—"}</td>
                  <td className="px-4 py-2 capitalize">{m.role}</td>
                </tr>
              ))}
              {members.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-muted-foreground">
                    No members loaded (login as org user)
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Invite teammate</h2>
        <form onSubmit={invite} className="flex flex-wrap gap-2">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="email@company.com"
            className="min-w-[220px] flex-1 rounded-md border bg-background px-3 py-2 text-sm"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="rounded-md border bg-background px-3 py-2 text-sm"
          >
            <option value="member">member</option>
            <option value="viewer">viewer</option>
            <option value="editor">editor</option>
            <option value="admin">admin</option>
          </select>
          <button
            type="submit"
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            Send invite
          </button>
        </form>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Pending invites</h2>
        <ul className="divide-y rounded-lg border">
          {invites
            .filter((i) => i.status === "pending")
            .map((i) => (
              <li key={i.id} className="flex items-center justify-between px-4 py-3 text-sm">
                <span>
                  {i.email} · <span className="capitalize">{i.role}</span>
                </span>
                <span className="text-xs text-muted-foreground">{i.status}</span>
              </li>
            ))}
          {invites.filter((i) => i.status === "pending").length === 0 && (
            <li className="px-4 py-6 text-center text-sm text-muted-foreground">No pending invites</li>
          )}
        </ul>
      </section>
    </div>
  );
}
