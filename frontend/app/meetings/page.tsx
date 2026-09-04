import Link from "next/link";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function MeetingsPage() {
  let data: Awaited<ReturnType<typeof api.listMeetings>> | null = null;
  let error: string | null = null;

  try {
    data = await api.listMeetings(1);
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load";
  }

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Meetings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {data ? `${data.total} total` : "—"}
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-secondary/50 text-left text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">Title</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Language</th>
              <th className="px-4 py-3 font-medium">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {items.map((m) => (
              <tr key={m.id} className="hover:bg-secondary/30">
                <td className="px-4 py-3">
                  <Link
                    href={`/meetings/${m.id}`}
                    className="font-medium text-foreground hover:text-primary"
                  >
                    {m.title}
                  </Link>
                  {m.executive_summary && (
                    <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
                      {m.executive_summary}
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 capitalize">{m.status}</td>
                <td className="px-4 py-3 uppercase">{m.language}</td>
                <td className="px-4 py-3 text-muted-foreground">
                  {new Date(m.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-muted-foreground">
                  No meetings found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
