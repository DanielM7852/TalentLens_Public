"use client";

import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { SKILL_FILTER_OPTIONS } from "@/lib/constants";
import type { SearchFilters } from "@/lib/types";
import { cn } from "@/lib/utils";

interface FilterPanelProps {
  filters: SearchFilters;
  onChange: (next: SearchFilters) => void;
  className?: string;
}

export function FilterPanel({ filters, onChange, className }: FilterPanelProps) {
  const toggleSkill = (skill: string) => {
    const selected = filters.skills.includes(skill)
      ? filters.skills.filter((s) => s !== skill)
      : [...filters.skills, skill];
    onChange({ ...filters, skills: selected });
  };

  return (
    <div className={cn("flex flex-col gap-6", className)}>
      <div>
        <Label className="text-sm font-medium">Skills</Label>
        <p className="mt-1 text-xs text-muted-foreground">
          Sent to the API as required skill filters.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {SKILL_FILTER_OPTIONS.map((skill) => {
            const active = filters.skills.includes(skill);
            return (
              <button
                key={skill}
                type="button"
                onClick={() => toggleSkill(skill)}
                className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Badge
                  variant={active ? "default" : "outline"}
                  className={cn(
                    "cursor-pointer transition-colors",
                    active && "ring-1 ring-primary/30"
                  )}
                >
                  {skill}
                </Badge>
              </button>
            );
          })}
        </div>
      </div>

      <Separator />

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="grad-min">Grad year (min)</Label>
          <Input
            id="grad-min"
            type="number"
            min={2020}
            max={2035}
            placeholder="2025"
            className="mt-1.5"
            value={filters.gradYearMin ?? ""}
            onChange={(e) =>
              onChange({
                ...filters,
                gradYearMin: e.target.value ? Number(e.target.value) : null,
              })
            }
          />
        </div>
        <div>
          <Label htmlFor="grad-max">Grad year (max)</Label>
          <Input
            id="grad-max"
            type="number"
            min={2020}
            max={2035}
            placeholder="2028"
            className="mt-1.5"
            value={filters.gradYearMax ?? ""}
            onChange={(e) =>
              onChange({
                ...filters,
                gradYearMax: e.target.value ? Number(e.target.value) : null,
              })
            }
          />
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        Exact grad year is sent to the API when min and max match; otherwise
        results are narrowed in the browser.
      </p>

      <Separator />

      <div>
        <Label htmlFor="major-filter">Major contains</Label>
        <Input
          id="major-filter"
          type="text"
          placeholder="e.g. Computer Science"
          className="mt-1.5"
          value={filters.major}
          onChange={(e) => onChange({ ...filters, major: e.target.value })}
        />
      </div>
    </div>
  );
}
