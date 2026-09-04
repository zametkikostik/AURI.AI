"use client";

import { useMemo, useState } from "react";

export function TranscriptTimeline({ text }: { text: string }) {
  const [q, setQ] = useState("");

  const paragraphs = useMemo(() => {
    if (!text) return [];
    return text
      .split(/\n{2,}|\r\n{2,}/)
      .map((p) => p.trim())
      .filter(Boolean);
  }, [text]);

  const filtered = useMemo(() => {
    if (!q.trim()) return paragraphs;
    const needle = q.toLowerCase();
    return paragraphs.filter((p) => p.toLowerCase().includes(needle));
  }, [paragraphs, q]);

  if (!text) {
    return (
      <div className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
        No transcript yet
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search inside transcript…"
        className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none ring-primary focus:ring-2"
      />
      <div className="max-h-[480px] space-y-2 overflow-y-auto rounded-lg border bg-card p-4">
        {filtered.map((p, i) => (
          <p
            key={i}
            className="border-l-2 border-transparent pl-3 text-sm leading-relaxed hover:border-primary/40"
          >
            {highlight(p, q)}
          </p>
        ))}
        {filtered.length === 0 && (
          <p className="text-sm text-muted-foreground">No matches</p>
        )}
      </div>
    </div>
  );
}

function highlight(text: string, query: string) {
  if (!query.trim()) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx < 0) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="rounded bg-amber-200 px-0.5 text-foreground">
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </>
  );
}
