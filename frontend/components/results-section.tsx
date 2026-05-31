"use client";

import { ResumeCard } from "@/components/resume-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ResumeSearchResult } from "@/lib/types";
import { AlertCircle, Search } from "lucide-react";

interface ResultsSectionProps {
  loading: boolean;
  error: string | null;
  results: ResumeSearchResult[];
  query: string;
  elapsedMs: number | null;
  hasSearched: boolean;
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
  onRetry?: () => void;
}

function ResultSkeletons() {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="space-y-3 rounded-xl border p-4">
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
          <div className="flex gap-2">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-5 w-14 rounded-full" />
          </div>
          <Skeleton className="h-16 w-full" />
        </div>
      ))}
    </div>
  );
}

export function ResultsSection({
  loading,
  error,
  results,
  query,
  elapsedMs,
  hasSearched,
  selectedIndex,
  onSelectIndex,
  onRetry,
}: ResultsSectionProps) {
  if (loading) {
    return (
      <div className="space-y-4" aria-busy="true" aria-live="polite">
        <Skeleton className="h-4 w-48" />
        <ResultSkeletons />
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="flex flex-col items-center justify-center rounded-xl border border-destructive/30 bg-destructive/5 px-6 py-14 text-center"
        role="alert"
      >
        <AlertCircle className="mb-3 size-10 text-destructive" aria-hidden />
        <h2 className="text-lg font-medium">Search failed</h2>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">{error}</p>
        {onRetry && (
          <Button type="button" variant="outline" className="mt-4" onClick={onRetry}>
            Try again
          </Button>
        )}
      </div>
    );
  }

  if (!hasSearched) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
        <Search className="mb-4 size-10 text-muted-foreground" aria-hidden />
        <h2 className="text-lg font-medium">Search resumes</h2>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          Enter a job description or keywords above. Use filters to narrow by
          skills, graduation year, and major. Press ↑↓ to move between results
          and Enter to open a profile.
        </p>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
        <h2 className="text-lg font-medium">No matches</h2>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          Try broader keywords, fewer skill filters, or a wider graduation year
          range. The API requires a non-empty search query.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {elapsedMs !== null && (
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{results.length}</span>{" "}
          {results.length === 1 ? "result" : "results"} in{" "}
          <span className="font-medium text-foreground">{elapsedMs}ms</span>
          <span className="hidden sm:inline text-muted-foreground">
            {" "}
            · ↑↓ navigate · Enter open
          </span>
        </p>
      )}
      <div className="grid gap-4 sm:grid-cols-2" role="listbox" aria-label="Search results">
        {results.map((resume, index) => (
          <div
            key={resume.resume_id || resume.candidate_id || index}
            role="option"
            aria-selected={index === selectedIndex}
          >
            <ResumeCard
              resume={resume}
              query={query}
              selected={index === selectedIndex}
              tabIndex={index === selectedIndex ? 0 : -1}
              onFocus={() => onSelectIndex(index)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
