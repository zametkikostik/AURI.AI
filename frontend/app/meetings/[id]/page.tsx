import Link from "next/link";
import { api } from "@/lib/api";
import { notFound } from "next/navigation";
import { ExportButtons } from "@/components/meetings/export-buttons";
import { MeetingPlayerSection } from "@/components/meetings/meeting-player-section";

export const dynamic = "force-dynamic";

export default async function MeetingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let meeting: Awaited<ReturnType<typeof api.getMeeting>> | null = null;
  let knowledge: Record<string, unknown> | null = null;

  try {
    meeting = await api.getMeeting(id);
    try {
      knowledge = await api.getMeetingKnowledge(id);
    } catch {
      knowledge = null;
    }
  } catch {
    notFound();
  }

  if (!meeting) notFound();

  const actionItems = (meeting.action_items ?? []) as Array<{
    who?: string;
    what?: string;
    deadline?: string;
  }>;

  const recordingId = meeting.recordings?.[0]?.id;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/meetings" className="text-sm text-muted-foreground hover:text-primary">
            ← Meetings
          </Link>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">{meeting.title}</h1>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
            <span className="rounded-full bg-secondary px-2.5 py-0.5 capitalize">
              {meeting.status}
            </span>
            <span className="rounded-full bg-secondary px-2.5 py-0.5 uppercase">
              {meeting.language}
            </span>
            {meeting.duration_seconds != null && (
              <span className="rounded-full bg-secondary px-2.5 py-0.5">
                {Math.round(meeting.duration_seconds / 60)} min
              </span>
            )}
          </div>
        </div>
        <ExportButtons meetingId={meeting.id} />
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Executive summary</h2>
        <div className="rounded-lg border bg-card p-4 text-sm leading-relaxed">
          {meeting.executive_summary || (
            <span className="text-muted-foreground">Summary not available yet.</span>
          )}
        </div>
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="space-y-3">
          <h2 className="text-lg font-medium">Topics</h2>
          <div className="flex flex-wrap gap-2">
            {(meeting.topics ?? []).length > 0 ? (
              (meeting.topics ?? []).map((t) => (
                <span
                  key={t}
                  className="rounded-full bg-accent px-3 py-1 text-xs font-medium text-accent-foreground"
                >
                  {t}
                </span>
              ))
            ) : (
              <span className="text-sm text-muted-foreground">No topics</span>
            )}
          </div>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-medium">Action items</h2>
          {actionItems.length > 0 ? (
            <ul className="space-y-2">
              {actionItems.map((a, i) => (
                <li key={i} className="rounded-md border px-3 py-2 text-sm">
                  <span className="font-medium">{a.what}</span>
                  {(a.who || a.deadline) && (
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {a.who && <span>Owner: {a.who}</span>}
                      {a.deadline && <span> · Due: {a.deadline}</span>}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No action items</p>
          )}
        </section>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Player & transcript</h2>
        <MeetingPlayerSection
          meetingId={meeting.id}
          recordingId={recordingId}
          fullText={meeting.transcript?.full_text}
        />
      </section>

      {knowledge && (knowledge as { knowledge?: unknown }).knowledge && (
        <section className="space-y-3">
          <h2 className="text-lg font-medium">Knowledge extract</h2>
          <pre className="max-h-64 overflow-auto rounded-lg border bg-secondary/30 p-4 text-xs">
            {JSON.stringify((knowledge as { knowledge: unknown }).knowledge, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}
