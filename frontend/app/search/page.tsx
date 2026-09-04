"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Search as SearchIcon } from "lucide-react";

type HybridResult = {
  query: string;
  semantic: Array<{
    score: number;
    meeting_id?: string;
    meeting_title?: string;
    text?: string;
  }>;
  keyword: Array<{
    meeting_id: string;
    meeting_title: string;
    snippet?: string;
    executive_summary?: string;
  }>;
};

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<HybridResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.hybridSearch(query.trim(), 12);
      setResult(data as HybridResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Knowledge Hub</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Semantic + keyword search across all meetings (org-scoped)
        </p>
      </div>

      <form onSubmit={onSearch} className="flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search decisions, people, topics..."
            className="w-full rounded-lg border bg-background py-2.5 pl-10 pr-4 text-sm outline-none ring-primary focus:ring-2"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="grid gap-8 lg:grid-cols-2">
          <section className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Semantic ({result.semantic?.length ?? 0})
            </h2>
            <div className="space-y-2">
              {(result.semantic ?? []).map((hit, i) => (
                <a
                  key={i}
                  href={hit.meeting_id ? `/meetings/${hit.meeting_id}` : "#"}
                  className="block rounded-lg border p-3 transition-colors hover:bg-secondary/40"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">
                      {hit.meeting_title || "Meeting"}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {(hit.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-3 text-xs text-muted-foreground">{hit.text}</p>
                </a>
              ))}
              {(result.semantic ?? []).length === 0 && (
                <p className="text-sm text-muted-foreground">No semantic hits</p>
              )}
            </div>
          </section>

          <section className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Keyword ({result.keyword?.length ?? 0})
            </h2>
            <div className="space-y-2">
              {(result.keyword ?? []).map((hit, i) => (
                <a
                  key={i}
                  href={`/meetings/${hit.meeting_id}`}
                  className="block rounded-lg border p-3 transition-colors hover:bg-secondary/40"
                >
                  <div className="text-sm font-medium">{hit.meeting_title}</div>
                  <p className="mt-1 line-clamp-3 text-xs text-muted-foreground">
                    {hit.snippet || hit.executive_summary || "—"}
                  </p>
                </a>
              ))}
              {(result.keyword ?? []).length === 0 && (
                <p className="text-sm text-muted-foreground">No keyword hits</p>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
