"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Segment = {
  start?: number | null;
  end?: number | null;
  text?: string;
  word?: string;
};

type Props = {
  src?: string | null;
  segments?: Segment[] | null;
  fullText?: string | null;
};

export function SyncedPlayer({ src, segments, fullText }: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [t, setT] = useState(0);
  const [duration, setDuration] = useState(0);

  const items = useMemo(() => {
    if (segments && segments.length) {
      return segments
        .map((s) => ({
          start: Number(s.start ?? 0),
          end: Number(s.end ?? s.start ?? 0),
          text: (s.text || s.word || "").trim(),
        }))
        .filter((s) => s.text);
    }
    if (!fullText) return [];
    const parts = fullText.split(/(?<=[.!?])\s+/).filter(Boolean);
    return parts.map((text, i) => ({
      start: i * 5,
      end: i * 5 + 5,
      text,
    }));
  }, [segments, fullText]);

  const activeIdx = useMemo(() => {
    if (!items.length) return -1;
    let idx = 0;
    for (let i = 0; i < items.length; i++) {
      if (t >= items[i].start) idx = i;
    }
    return idx;
  }, [items, t]);

  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;
    const onTime = () => setT(el.currentTime);
    const onMeta = () => setDuration(el.duration || 0);
    const onEnd = () => setPlaying(false);
    el.addEventListener("timeupdate", onTime);
    el.addEventListener("loadedmetadata", onMeta);
    el.addEventListener("ended", onEnd);
    return () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("loadedmetadata", onMeta);
      el.removeEventListener("ended", onEnd);
    };
  }, [src]);

  function toggle() {
    const el = audioRef.current;
    if (!el || !src) return;
    if (playing) {
      el.pause();
      setPlaying(false);
    } else {
      void el.play();
      setPlaying(true);
    }
  }

  function jump(start: number) {
    const el = audioRef.current;
    if (!el) return;
    el.currentTime = start;
    setT(start);
    if (!playing && src) {
      void el.play();
      setPlaying(true);
    }
  }

  return (
    <div className="space-y-3">
      <div className="rounded-lg border bg-card p-4">
        {src ? <audio ref={audioRef} src={src} preload="metadata" /> : null}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={toggle}
            disabled={!src}
            className="rounded-full bg-primary px-4 py-1.5 text-xs font-medium text-primary-foreground disabled:opacity-40"
          >
            {playing ? "Pause" : "Play"}
          </button>
          <input
            type="range"
            min={0}
            max={duration || 1}
            step={0.1}
            value={t}
            onChange={(e) => jump(Number(e.target.value))}
            className="flex-1"
            disabled={!src}
          />
          <span className="w-20 text-right text-xs tabular-nums text-muted-foreground">
            {fmt(t)} / {fmt(duration)}
          </span>
        </div>
        {!src && (
          <p className="mt-2 text-xs text-muted-foreground">
            No audio URL yet — use presigned recording URL when available.
          </p>
        )}
      </div>

      <div className="max-h-[360px] space-y-1 overflow-y-auto rounded-lg border bg-card p-3">
        {items.map((seg, i) => (
          <button
            key={i}
            type="button"
            onClick={() => jump(seg.start)}
            className={`block w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
              i === activeIdx
                ? "bg-accent text-accent-foreground"
                : "hover:bg-secondary/50"
            }`}
          >
            <span className="mr-2 text-[10px] tabular-nums text-muted-foreground">
              {fmt(seg.start)}
            </span>
            {seg.text}
          </button>
        ))}
        {items.length === 0 && (
          <p className="p-2 text-sm text-muted-foreground">No transcript segments</p>
        )}
      </div>
    </div>
  );
}

function fmt(sec: number) {
  if (!sec || Number.isNaN(sec)) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
