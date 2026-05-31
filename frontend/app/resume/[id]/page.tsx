"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ResumeDetailView } from "@/components/resume-detail-view";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, API_BASE_URL, fetchResume } from "@/lib/api";
import type { ResumeDetail } from "@/lib/types";
import { AlertCircle } from "lucide-react";
import Link from "next/link";

export default function ResumeDetailPage() {
  const params = useParams();
  const rawId = params?.id;
  const resumeId = decodeURIComponent(
    Array.isArray(rawId) ? rawId[0] ?? "" : rawId ?? ""
  );

  const [resume, setResume] = useState<ResumeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadResume = useCallback(async () => {
    if (!resumeId) {
      setError("Missing resume id.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await fetchResume(resumeId);
      setResume(data);
    } catch (err) {
      setResume(null);
      if (err instanceof ApiError) {
        setError(
          err.status === 404
            ? `Resume not found: ${resumeId}`
            : err.message
        );
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Could not load resume. Is the API running?");
      }
    } finally {
      setLoading(false);
    }
  }, [resumeId]);

  useEffect(() => {
    void loadResume();
  }, [loadResume]);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card/50 backdrop-blur-sm">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-xl font-semibold tracking-tight hover:underline sm:text-2xl"
            >
              TalentLens
            </Link>
            <Badge
              variant="secondary"
              className="text-[10px] font-medium uppercase tracking-wide"
            >
              by DS3
            </Badge>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8">
        {loading && (
          <div className="space-y-4" aria-busy="true">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-64" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        )}

        {!loading && error && (
          <div
            className="flex flex-col items-center rounded-xl border border-destructive/30 bg-destructive/5 px-6 py-14 text-center"
            role="alert"
          >
            <AlertCircle className="mb-3 size-10 text-destructive" aria-hidden />
            <h1 className="text-lg font-medium">Could not load resume</h1>
            <p className="mt-2 max-w-md text-sm text-muted-foreground">{error}</p>
            <p className="mt-2 text-xs text-muted-foreground">API: {API_BASE_URL}</p>
            <div className="mt-4 flex gap-2">
              <Button type="button" variant="outline" onClick={() => void loadResume()}>
                Retry
              </Button>
              <Link
                href="/"
                className="inline-flex h-8 items-center justify-center rounded-lg bg-secondary px-3 text-sm font-medium text-secondary-foreground hover:bg-secondary/80"
              >
                Back to search
              </Link>
            </div>
          </div>
        )}

        {!loading && !error && resume && <ResumeDetailView resume={resume} />}
      </main>
    </div>
  );
}
