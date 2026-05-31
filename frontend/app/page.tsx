"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FilterPanel } from "@/components/filter-panel";
import { ResultsSection } from "@/components/results-section";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ApiError, API_BASE_URL, resumeDetailPath, searchResumes } from "@/lib/api";
import type { ResumeSearchResult, SearchFilters } from "@/lib/types";
import { SlidersHorizontal } from "lucide-react";

const DEBOUNCE_MS = 300;

const DEFAULT_FILTERS: SearchFilters = {
  skills: [],
  gradYearMin: null,
  gradYearMax: null,
  major: "",
};

function isTypingTarget(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || target.isContentEditable;
}

export default function HomePage() {
  const router = useRouter();
  const searchInputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [filters, setFilters] = useState<SearchFilters>(DEFAULT_FILTERS);
  const [results, setResults] = useState<ResumeSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQuery(query);
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [query]);

  const filtersKey = useMemo(() => JSON.stringify(filters), [filters]);

  const executeSearch = useCallback(async () => {
    const trimmed = debouncedQuery.trim();
    if (!trimmed) {
      setResults([]);
      setElapsedMs(null);
      setHasSearched(false);
      setError(null);
      setLoading(false);
      setSelectedIndex(-1);
      return;
    }

    setLoading(true);
    setError(null);
    setHasSearched(true);
    setSelectedIndex(-1);

    try {
      const { results: nextResults, elapsedMs: ms } = await searchResumes(
        trimmed,
        filters,
        20
      );
      setResults(nextResults);
      setElapsedMs(ms);
      setSelectedIndex(nextResults.length > 0 ? 0 : -1);
    } catch (err) {
      setResults([]);
      setElapsedMs(null);
      setSelectedIndex(-1);
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred. Check that the API is running.");
      }
    } finally {
      setLoading(false);
    }
  }, [debouncedQuery, filters]);

  useEffect(() => {
    void executeSearch();
  }, [debouncedQuery, filtersKey, executeSearch]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target)) return;
      if (results.length === 0 || loading || error) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => {
          const next = i < 0 ? 0 : Math.min(i + 1, results.length - 1);
          return next;
        });
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => {
          const next = i <= 0 ? 0 : i - 1;
          return next;
        });
      } else if (e.key === "Enter" && selectedIndex >= 0) {
        e.preventDefault();
        const row = results[selectedIndex];
        const id = row.resume_id || row.candidate_id;
        if (id) {
          router.push(resumeDetailPath(id));
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [results, loading, error, selectedIndex, router]);

  const hasActiveFilters =
    filters.skills.length > 0 ||
    filters.gradYearMin !== null ||
    filters.gradYearMax !== null ||
    filters.major.trim().length > 0;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card/50 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
              TalentLens
            </h1>
            <Badge
              variant="secondary"
              className="text-[10px] font-medium uppercase tracking-wide"
            >
              by DS3
            </Badge>
          </div>
          <p className="hidden truncate text-xs text-muted-foreground sm:block">
            API: {API_BASE_URL}
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <div className="mb-6 flex flex-col gap-3 sm:mb-8">
          <label htmlFor="search" className="sr-only">
            Search resumes
          </label>
          <Input
            ref={searchInputRef}
            id="search"
            type="search"
            placeholder="Job description or skills (e.g. Python, machine learning)…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-12 text-base shadow-sm"
            autoComplete="off"
          />
          <p className="text-center text-xs text-muted-foreground sm:text-left">
            Live search · debounced {DEBOUNCE_MS}ms ·{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-[11px]">
              POST /api/search
            </code>
          </p>
        </div>

        <div className="flex gap-6 lg:gap-8">
          <aside className="hidden w-64 shrink-0 lg:block xl:w-72">
            <div className="sticky top-6 rounded-xl border bg-card p-4 shadow-sm">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Filters
              </h2>
              <FilterPanel filters={filters} onChange={setFilters} />
            </div>
          </aside>

          <div className="min-w-0 flex-1 space-y-4">
            <div className="flex items-center justify-between lg:hidden">
              <Sheet>
                <SheetTrigger
                  render={
                    <Button variant="outline" size="sm" className="gap-2" />
                  }
                >
                  <SlidersHorizontal className="size-4" />
                  Filters
                  {hasActiveFilters && (
                    <Badge variant="default" className="ml-1 h-5 min-w-5 px-1">
                      !
                    </Badge>
                  )}
                </SheetTrigger>
                <SheetContent
                  side="left"
                  className="w-[min(100%,20rem)] overflow-y-auto"
                >
                  <SheetHeader>
                    <SheetTitle>Filters</SheetTitle>
                    <SheetDescription>
                      Skills, graduation year, and major are applied via the API
                      or client-side range.
                    </SheetDescription>
                  </SheetHeader>
                  <div className="px-4 pb-6">
                    <FilterPanel filters={filters} onChange={setFilters} />
                  </div>
                </SheetContent>
              </Sheet>
              <p className="truncate text-xs text-muted-foreground">
                {API_BASE_URL}
              </p>
            </div>

            <ResultsSection
              loading={loading}
              error={error}
              results={results}
              query={debouncedQuery}
              elapsedMs={elapsedMs}
              hasSearched={hasSearched}
              selectedIndex={selectedIndex}
              onSelectIndex={setSelectedIndex}
              onRetry={() => void executeSearch()}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
