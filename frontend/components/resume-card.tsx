"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { resumeDetailPath } from "@/lib/api";
import { highlightSnippet } from "@/lib/highlight";
import type { ResumeSearchResult } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ResumeCardProps {
  resume: ResumeSearchResult;
  query: string;
  selected?: boolean;
  tabIndex?: number;
  onFocus?: () => void;
}

function scoreColor(score: number): string {
  if (score >= 0.85) return "text-emerald-600 dark:text-emerald-400";
  if (score >= 0.7) return "text-amber-600 dark:text-amber-400";
  return "text-muted-foreground";
}

export function ResumeCard({
  resume,
  query,
  selected = false,
  tabIndex = -1,
  onFocus,
}: ResumeCardProps) {
  const skills = resume.matched_skills ?? [];
  const topSkills = skills.slice(0, 4);
  const scorePct = Math.round(resume.score * 100);
  const snippet =
    resume.text_preview?.trim() ||
    resume.grok_summary?.trim() ||
    "No preview available.";
  const href = resumeDetailPath(resume.resume_id || resume.candidate_id);
  const displayName = resume.full_name || resume.filename;

  return (
    <Link
      href={href}
      className="block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      tabIndex={tabIndex}
      onFocus={onFocus}
      aria-current={selected ? "true" : undefined}
    >
      <Card
        className={cn(
          "flex h-full flex-col border-border/80 shadow-sm transition-shadow hover:shadow-md",
          selected && "ring-2 ring-primary ring-offset-2 ring-offset-background"
        )}
      >
        <CardHeader className="space-y-2 pb-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <CardTitle className="truncate text-lg">{displayName}</CardTitle>
              <CardDescription className="truncate">
                {resume.major || "—"}
              </CardDescription>
            </div>
            <div className="shrink-0 text-right">
              <p
                className={`text-2xl font-semibold tabular-nums ${scoreColor(resume.score)}`}
              >
                {scorePct}%
              </p>
              <p className="text-xs text-muted-foreground">match</p>
            </div>
          </div>
          {topSkills.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {topSkills.map((skill) => (
                <Badge key={skill} variant="secondary" className="font-normal">
                  {skill}
                </Badge>
              ))}
              {skills.length > 4 && (
                <Badge variant="outline" className="font-normal">
                  +{skills.length - 4}
                </Badge>
              )}
            </div>
          )}
        </CardHeader>
        <CardContent className="mt-auto pt-0">
          <p className="line-clamp-4 text-sm leading-relaxed text-muted-foreground">
            {highlightSnippet(snippet, query)}
          </p>
          {resume.graduation_year && (
            <p className="mt-3 text-xs text-muted-foreground">
              Class of {resume.graduation_year}
              {resume.rank > 0 && ` · Rank #${resume.rank}`}
            </p>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
