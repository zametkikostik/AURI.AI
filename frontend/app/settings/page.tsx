"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function token() {
  return typeof window !== "undefined"
    ? localStorage.getItem("auri_access_token")
    : null;
}

type Settings = {
  ai_mode: string;
  slack_webhook_configured: boolean;
  notion_configured: boolean;
  zapier_configured: boolean;
  notify_on_ready: boolean;
  notify_slack: boolean;
  notify_notion: boolean;
  slack_webhook_hint?: string | null;
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [slackUrl, setSlackUrl] = useState("");
  const [notionToken, setNotionToken] = useState("");
  const [notionDb, setNotionDb] = useState("");
  const [aiMode, setAiMode] = useState("strict_private");
  const [notifyOnReady, setNotifyOnReady] = useState(true);
  const [notifySlack, setNotifySlack] = useState(false);
  const [notifyNotion, setNotifyNotion] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    const t = token();
    if (!t) {
      setErr("Login required");
      return;
    }
    const res = await fetch(`${API}/api/v1/settings/organization`, {
      headers: { Authorization: `Bearer ${t}` },
    });
    if (!res.ok) {
      setErr(`Load failed: ${res.status}`);
      return;
    }
    const data = (await res.json()) as Settings;
    setSettings(data);
    setAiMode(data.ai_mode);
    setNotifyOnReady(data.notify_on_ready);
    setNotifySlack(data.notify_slack);
    setNotifyNotion(data.notify_notion);
  }

  useEffect(() => {
    void load();
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    const t = token();
    if (!t) return;
    const body: Record<string, unknown> = {
      ai_mode: aiMode,
      notify_on_ready: notifyOnReady,
      notify_slack: notifySlack,
      notify_notion: notifyNotion,
    };
    if (slackUrl) body.slack_webhook_url = slackUrl;
    if (notionToken) body.notion_token = notionToken;
    if (notionDb) body.notion_database_id = notionDb;

    const res = await fetch(`${API}/api/v1/settings/organization`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${t}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      setErr(`Save failed: ${res.status} ${await res.text()}`);
      return;
    }
    setMsg("Saved");
    setSlackUrl("");
    setNotionToken("");
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Organization privacy mode and integrations
        </p>
      </div>

      {err && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {err}
        </div>
      )}
      {msg && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {msg}
        </div>
      )}

      <form onSubmit={save} className="space-y-6">
        <section className="rounded-lg border p-5 space-y-3">
          <h2 className="font-medium">Privacy / AI mode</h2>
          <select
            value={aiMode}
            onChange={(e) => setAiMode(e.target.value)}
            className="w-full max-w-md rounded-md border bg-background px-3 py-2 text-sm"
          >
            <option value="strict_private">Strict Private (Ollama only)</option>
            <option value="hybrid">Hybrid</option>
            <option value="cloud">Cloud</option>
          </select>
          <p className="text-xs text-muted-foreground">
            Strict private keeps transcripts and summaries on your infrastructure.
          </p>
        </section>

        <section className="rounded-lg border p-5 space-y-3">
          <h2 className="font-medium">Notifications</h2>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={notifyOnReady}
              onChange={(e) => setNotifyOnReady(e.target.checked)}
            />
            Notify when meeting is ready
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={notifySlack}
              onChange={(e) => setNotifySlack(e.target.checked)}
            />
            Slack (summary only)
            {settings?.slack_webhook_configured && (
              <span className="text-xs text-muted-foreground">
                configured {settings.slack_webhook_hint}
              </span>
            )}
          </label>
          <input
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            placeholder="Slack webhook URL (leave blank to keep existing)"
            value={slackUrl}
            onChange={(e) => setSlackUrl(e.target.value)}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={notifyNotion}
              onChange={(e) => setNotifyNotion(e.target.checked)}
            />
            Notion export on ready
            {settings?.notion_configured && (
              <span className="text-xs text-muted-foreground">configured</span>
            )}
          </label>
          <input
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            placeholder="Notion integration token"
            value={notionToken}
            onChange={(e) => setNotionToken(e.target.value)}
          />
          <input
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            placeholder="Notion database ID"
            value={notionDb}
            onChange={(e) => setNotionDb(e.target.value)}
          />
        </section>

        <button
          type="submit"
          className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground"
        >
          Save settings
        </button>
      </form>
    </div>
  );
}
