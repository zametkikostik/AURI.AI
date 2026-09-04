"use client";

import { useEffect, useState } from "react";
import { SyncedPlayer } from "@/components/meetings/synced-player";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function MeetingPlayerSection({
  meetingId,
  recordingId,
  fullText,
}: {
  meetingId: string;
  recordingId?: string;
  fullText?: string | null;
}) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    if (!recordingId) return;
    const t = localStorage.getItem("auri_access_token");
    if (!t) return;
    void fetch(`${API}/api/v1/meetings/${meetingId}/recordings/${recordingId}/url`, {
      headers: { Authorization: `Bearer ${t}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.url) setSrc(data.url);
      })
      .catch(() => undefined);
  }, [meetingId, recordingId]);

  return <SyncedPlayer src={src} fullText={fullText} />;
}
