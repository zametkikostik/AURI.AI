"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function token() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auri_access_token");
}

export function ExportButtons({ meetingId }: { meetingId: string }) {
  async function download(format: "json" | "md" | "txt") {
    const t = token();
    const res = await fetch(
      `${API_BASE}/api/v1/exports/meetings/${meetingId}?format=${format}`,
      { headers: t ? { Authorization: `Bearer ${t}` } : {} }
    );
    if (!res.ok) {
      alert(`Export failed: ${res.status}`);
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `meeting.${format === "md" ? "md" : format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex flex-wrap gap-2">
      {(["json", "md", "txt"] as const).map((f) => (
        <button
          key={f}
          type="button"
          onClick={() => download(f)}
          className="rounded-md border bg-card px-3 py-1.5 text-xs font-medium hover:bg-secondary"
        >
          Export .{f}
        </button>
      ))}
    </div>
  );
}
