import Link from "next/link";
import { api } from "@/lib/api";
import { Calendar, Search, Shield, Upload } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let meetings: Awaited<ReturnType<typeof api.listMeetings>> | null = null;
  let health: Awaited<ReturnType<typeof api.health>> | null = null;
  let error: string | null = null;

  try {
    [meetings, health] = await Promise.all([api.listMeetings(1), api.health()]);
  } catch (e) {
    error = e instanceof Error ? e.message : "API unavailable";
  }

  const items = meetings?.items ?? [];
  const ready = items.filter((m) => m.status === "ready").length;
  const processing = items.filter((m) => m.status === "processing").length;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Privacy-first meeting intelligence for your team
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Backend offline or unreachable: {error}. Start API on :8000.
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Meetings" value={meetings?.total ?? "—"} icon={<Calendar className="h-4 w-4" />} />
        <StatCard label="Ready" value={ready} icon={<Upload className="h-4 w-4" />} />
        <StatCard label="Processing" value={processing} icon={<Search className="h-4 w-4" />} />
        <StatCard label="AI Mode" value={health?.ai_mode ?? "—"} icon={<Shield className="h-4 w-4" />} />
      </div>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-medium">Recent meetings</h2>
          <Link href="/meetings" className="text-sm text-primary hover:underline">
            View all
          </Link>
        </div>

        {items.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="divide-y rounded-lg border">
            {items.slice(0, 8).map((m) => (
              <Link
                key={m.id}
                href={`/meetings/${m.id}`}
                className="flex items-center justify-between px-4 py-3 transition-colors hover:bg-secondary/50"
              >
                <div>
                  <div className="font-medium">{m.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {new Date(m.created_at).toLocaleString()}
                    {m.topics?.length ? ` · ${m.topics.slice(0, 3).join(", ")}` : ""}
                  </div>
                </div>
                <StatusBadge status={m.status} />
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between text-muted-foreground">
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
        {icon}
      </div>
      <div className="mt-2 text-2xl font-semibold capitalize">{value}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ready: "bg-emerald-100 text-emerald-700",
    processing: "bg-amber-100 text-amber-700",
    failed: "bg-red-100 text-red-700",
    scheduled: "bg-slate-100 text-slate-600",
  };
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
        colors[status] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {status}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="rounded-lg border border-dashed px-6 py-12 text-center">
      <p className="text-sm text-muted-foreground">
        No meetings yet. Create one via API or go to Meetings.
      </p>
      <Link href="/meetings" className="mt-3 inline-block text-sm font-medium text-primary hover:underline">
        Open Meetings →
      </Link>
    </div>
  );
}
