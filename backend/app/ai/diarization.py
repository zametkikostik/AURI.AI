"""Speaker diarization: pyannote if available, else heuristic fallback."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def diarize_with_pyannote(audio_path: str) -> list[dict[str, Any]] | None:
    token = getattr(settings, "hf_token", None)
    if not token:
        return None
    try:
        from pyannote.audio import Pipeline

        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=token,
        )
        diarization = pipeline(audio_path)
        segments: list[dict[str, Any]] = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(
                {"start": float(turn.start), "end": float(turn.end), "speaker": str(speaker)}
            )
        logger.info("pyannote_diarization_done", segments=len(segments))
        return segments
    except Exception as e:
        logger.warning("pyannote_unavailable", error=str(e))
        return None


def assign_speakers_heuristic(
    words: list[dict[str, Any]], max_gap: float = 1.2
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not words:
        return [], []

    segments: list[dict[str, Any]] = []
    speakers_set: dict[str, float] = {}
    current_speaker = 0
    buf: list[dict[str, Any]] = []
    seg_start = None
    last_end = None

    def flush():
        nonlocal buf, seg_start, current_speaker
        if not buf:
            return
        text = " ".join((w.get("word") or w.get("text") or "").strip() for w in buf).strip()
        sp = f"SPEAKER_{current_speaker:02d}"
        start = seg_start if seg_start is not None else buf[0].get("start")
        end = buf[-1].get("end")
        duration = float(end or 0) - float(start or 0)
        speakers_set[sp] = speakers_set.get(sp, 0) + max(duration, 0)
        segments.append({"start": start, "end": end, "text": text, "speaker": sp})
        buf = []
        seg_start = None

    for w in words:
        start = w.get("start")
        end = w.get("end")
        if last_end is not None and start is not None:
            if float(start) - float(last_end) > max_gap:
                flush()
                current_speaker = (current_speaker + 1) % 4
        if not buf:
            seg_start = start
        buf.append(w)
        last_end = end
    flush()

    speakers = [
        {"id": sid, "name": sid.replace("_", " ").title(), "total_speaking_time": round(t, 2)}
        for sid, t in speakers_set.items()
    ]
    return segments, speakers


def merge_diarization_with_words(
    words: list[dict[str, Any]], diar_segments: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not words or not diar_segments:
        return assign_speakers_heuristic(words)

    labeled = []
    for w in words:
        mid = None
        if w.get("start") is not None and w.get("end") is not None:
            mid = (float(w["start"]) + float(w["end"])) / 2
        speaker = None
        if mid is not None:
            for d in diar_segments:
                if float(d["start"]) <= mid <= float(d["end"]):
                    speaker = d["speaker"]
                    break
        labeled.append({**w, "speaker": speaker or "SPEAKER_00"})

    segments: list[dict[str, Any]] = []
    speakers_time: dict[str, float] = {}
    buf: list[dict[str, Any]] = []
    current_sp = None

    def flush():
        nonlocal buf, current_sp
        if not buf:
            return
        text = " ".join((x.get("word") or x.get("text") or "").strip() for x in buf)
        start, end = buf[0].get("start"), buf[-1].get("end")
        sp = current_sp or "SPEAKER_00"
        speakers_time[sp] = speakers_time.get(sp, 0) + max(float(end or 0) - float(start or 0), 0)
        segments.append({"start": start, "end": end, "text": text.strip(), "speaker": sp})
        buf = []

    for w in labeled:
        sp = w.get("speaker")
        if current_sp is None:
            current_sp = sp
        if sp != current_sp:
            flush()
            current_sp = sp
        buf.append(w)
    flush()

    speakers = [
        {"id": s, "name": s.replace("_", " ").title(), "total_speaking_time": round(t, 2)}
        for s, t in speakers_time.items()
    ]
    return segments, speakers
