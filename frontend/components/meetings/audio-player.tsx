"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  src?: string | null;
  title?: string;
};

export function AudioPlayer({ src, title }: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;
    const onTime = () => setProgress(el.currentTime);
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

  if (!src) {
    return (
      <div className="rounded-lg border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
        No playable audio URL. Upload a recording or configure presigned playback.
      </div>
    );
  }

  function toggle() {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
      setPlaying(false);
    } else {
      void el.play();
      setPlaying(true);
    }
  }

  function seek(value: number) {
    const el = audioRef.current;
    if (!el) return;
    el.currentTime = value;
    setProgress(value);
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="mb-2 text-sm font-medium">{title || "Recording"}</div>
      <audio ref={audioRef} src={src} preload="metadata" />
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={toggle}
          className="rounded-full bg-primary px-4 py-1.5 text-xs font-medium text-primary-foreground"
        >
          {playing ? "Pause" : "Play"}
        </button>
        <input
          type="range"
          min={0}
          max={duration || 0}
          step={0.1}
          value={progress}
          onChange={(e) => seek(Number(e.target.value))}
          className="flex-1"
        />
        <span className="w-20 text-right text-xs text-muted-foreground tabular-nums">
          {fmt(progress)} / {fmt(duration)}
        </span>
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
