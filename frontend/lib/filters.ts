import type { ResumeSearchResult, SearchFilters } from "@/lib/types";

export function filtersToApiBody(filters: SearchFilters): Record<string, unknown> {
  const body: Record<string, unknown> = {
    input_mode: "Job Description",
  };

  if (filters.skills.length > 0) {
    body.skill_filters = filters.skills;
  }

  if (
    filters.gradYearMin !== null &&
    filters.gradYearMax !== null &&
    filters.gradYearMin === filters.gradYearMax
  ) {
    body.grad_year_filter = String(filters.gradYearMin);
  }

  const major = filters.major.trim();
  if (major) {
    body.major_filter = major;
  }

  return body;
}

export function applyClientFilters(
  results: ResumeSearchResult[],
  filters: SearchFilters
): ResumeSearchResult[] {
  return results.filter((row) => {
    const year = parseInt(row.graduation_year, 10);
    if (
      filters.gradYearMin !== null &&
      !Number.isNaN(year) &&
      year < filters.gradYearMin
    ) {
      return false;
    }
    if (
      filters.gradYearMax !== null &&
      !Number.isNaN(year) &&
      year > filters.gradYearMax
    ) {
      return false;
    }
    if (filters.gradYearMin !== null && Number.isNaN(year)) {
      return false;
    }
    return true;
  });
}
