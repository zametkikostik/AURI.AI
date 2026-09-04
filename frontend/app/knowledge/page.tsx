"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n/context";
import { BookOpen, Search as SearchIcon } from "lucide-react";

type Topic = {
  name: string;
  count: number;
  example_meetings?: string[];
};

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

export default function KnowledgePage() {
  const { t } = useI18n();
  const [topics, setTopics] = useState<Topic[]>([]);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<HybridResult | null>(null);
  const [loadingTopics, setLoadingTopics] = useState(true);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingTopics(true);
      setError(null);
      try {
        const data = await api.listTopics();
        if (!cancelled) setTopics(data.topics ?? []);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load topics");
          setTopics([]);
        }
      } finally {
        if (!cancelled) setLoadingTopics(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredTopics = useMemo(() => {
    if (!filter.trim()) return topics;
    const q = filter.toLowerCase();
    return topics.filter((t) => t.name.toLowerCase().includes(q));
  }, [topics, filter]);

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoadingSearch(true);
    setError(null);
    try {
      const data = (await api.hybridSearch(query.trim(), 12)) as HybridResult;
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResult(null);
    } finally {
      setLoadingSearch(false);
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <BookOpen className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t.knowledge.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t.knowledge.subtitle}</p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-medium">{t.search.title}</h2>
        <form onSubmit={onSearch} className="flex gap-2">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t.search.placeholder}
              className="w-full rounded-lg border bg-background py-2.5 pl-10 pr-4 text-sm outline-none ring-primary focus:ring-2"
            />
          </div>
          <button
            type="submit"
            disabled={loadingSearch}
            className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {loadingSearch ? t.common.loading : t.common.search}
          </button>
        </form>

        {result && (
          <div className="grid gap-6 lg:grid-cols-2">
            <ResultColumn title={`${t.search.semantic} (${result.semantic?.length ?? 0})`}>
              {(result.semantic ?? []).map((hit, i) => (
                <ResultCard
                  key={i}
                  href={hit.meeting_id ? `/meetings/${hit.meeting_id}` : undefined}
                  title={hit.meeting_title || "Meeting"}
                  body={hit.text}
                  meta={typeof hit.score === "number" ? `${(hit.score * 100).toFixed(0)}%` : undefined}
                />
              ))}
              {(result.semantic ?? []).length === 0 && (
                <p className="text-sm text-muted-foreground">{t.common.noData}</p>
              )}
            </ResultColumn>
            <ResultColumn title={`${t.search.keyword} (${result.keyword?.length ?? 0})`}>
              {(result.keyword ?? []).map((hit, i) => (
                <ResultCard
                  key={i}
                  href={`/meetings/${hit.meeting_id}`}
                  title={hit.meeting_title}
                  body={hit.snippet || hit.executive_summary}
                />
              ))}
              {(result.keyword ?? []).length === 0 && (
                <p className="text-sm text-muted-foreground">{t.common.noData}</p>
              )}
            </ResultColumn>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-medium">{t.meetings.topics}</h2>
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder={t.common.search}
            className="w-full max-w-xs rounded-md border bg-background px-3 py-1.5 text-sm outline-none ring-primary focus:ring-2"
          />
        </div>

        {loadingTopics ? (
          <p className="text-sm text-muted-foreground">{t.common.loading}</p>
        ) : filteredTopics.length === 0 ? (
          <div className="rounded-lg border border-dashed px-6 py-10 text-center text-sm text-muted-foreground">
            {t.common.noData}
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {filteredTopics.map((topic) => (
              <div key={topic.name} className="rounded-lg border bg-card p-4 transition-colors hover:bg-secondary/30">
                <div className="flex items-start justify-between gap-2">
                  <button
                    type="button"
                    className="text-left text-sm font-medium hover:text-primary"
                    onClick={() => setQuery(topic.name)}
                  >
                    {topic.name}
                  </button>
                  <span className="rounded-full bg-secondary px-2 py-0.5 text-xs tabular-nums text-muted-foreground">
                    {topic.count}
                  </span>
                </div>
                {topic.example_meetings && topic.example_meetings.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {topic.example_meetings.slice(0, 2).map((title, i) => (
                      <li key={i} className="truncate text-xs text-muted-foreground">{title}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <p className="text-xs text-muted-foreground">
        Prefer a focused search view?{" "}
        <Link href="/search" className="text-primary hover:underline">{t.nav.search}</Link>
      </p>
    </div>
  );
}

function ResultColumn({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function ResultCard({
  href,
  title,
  body,
  meta,
}: {
  href?: string;
  title: string;
  body?: string | null;
  meta?: string;
}) {
  const inner = (
    <>
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">{title}</span>
        {meta && <span className="text-xs text-muted-foreground tabular-nums">{meta}</span>}
      </div>
      {body && <p className="mt-1 line-clamp-3 text-xs text-muted-foreground">{body}</p>}
    </>
  );
  if (href) {
    return (
      <Link href={href} className="block rounded-lg border p-3 transition-colors hover:bg-secondary/40">
        {inner}
      </Link>
    );
  }
  return <div className="rounded-lg border p-3">{inner}</div>;
}
