"use client";

import { useEffect, useState } from "react";

type Props = { organizationId?: string };

export function LiveStatus({ organizationId }: Props) {
  const [last, setLast] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!organizationId) return;
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const url = `${base}/api/v1/realtime/events?organization_id=${organizationId}`;
    const es = new EventSource(url);
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "meeting.ready") {
          setLast(`Ready: ${data.title || data.meeting_id}`);
        } else if (data.type === "connected") {
          setConnected(true);
        }
      } catch {
        /* ignore */
      }
    };
    return () => es.close();
  }, [organizationId]);

  if (!organizationId) return null;

  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          connected ? "bg-emerald-500" : "bg-slate-300"
        }`}
      />
      {connected ? "Live updates on" : "Connecting…"}
      {last && <span className="text-foreground">· {last}</span>}
    </div>
  );
}
