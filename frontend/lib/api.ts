import { filtersToApiBody } from "@/lib/filters";
import type { ResumeDetail, ResumeSearchResult, SearchFilters, SearchResponse } from "@/lib/types";

const DEFAULT_API = "http://localhost:8000";
const BASE_PATH = "/talentlens";
const SEARCH_TIMEOUT_MS = 120_000;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function isDeployedHost(hostname: string): boolean {
  return (
    hostname.endsWith(".vercel.app") ||
    hostname === "ds3atucsd.com" ||
    hostname.endsWith(".ds3atucsd.com")
  );
}

/**
 * Local dev: direct to localhost:8000 (or NEXT_PUBLIC_API_URL).
 * Vercel / production: same-origin /talentlens → proxied to Railway (next.config + vercel.json rewrites).
 */
export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return configured || DEFAULT_API;
    }
    if (isDeployedHost(host)) {
      return `${window.location.origin}${BASE_PATH}`;
    }
  }

  return configured || DEFAULT_API;
}

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? DEFAULT_API;

function networkErrorMessage(url: string, cause: unknown): string {
  const detail = cause instanceof Error ? cause.message : String(cause);
  return (
    `Could not reach the API at ${url}. (${detail}) ` +
    "Check Railway logs (OOM → set TALENTLENS_DISABLE_RERANKER=1) and redeploy Vercel after pushing the latest frontend."
  );
}

async function parseErrorMessage(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) {
      return data.detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join("; ");
    }
    return JSON.stringify(data);
  } catch {
    return res.statusText || `Request failed (${res.status})`;
  }
}

async function apiFetch(path: string, init: RequestInit): Promise<Response> {
  const base = getApiBaseUrl();
  const url = `${base}${path}`;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), SEARCH_TIMEOUT_MS);

  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new ApiError(
        0,
        `Search timed out after ${SEARCH_TIMEOUT_MS / 1000}s. Check Railway logs — the API may be out of memory.`
      );
    }
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(0, networkErrorMessage(url, err));
  } finally {
    window.clearTimeout(timer);
  }
}

export async function searchResumes(
  query: string,
  filters: SearchFilters,
  topK = 20
): Promise<SearchResponse> {
  const start = performance.now();
  const res = await apiFetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: query.trim(),
      top_k: topK,
      filters: filtersToApiBody(filters),
    }),
  });

  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorMessage(res));
  }

  const results = (await res.json()) as ResumeSearchResult[];

  return {
    results,
    elapsedMs: Math.round(performance.now() - start),
  };
}

export async function fetchResume(resumeId: string): Promise<ResumeDetail> {
  const res = await apiFetch(`/api/resume/${encodeURIComponent(resumeId)}`, {
    method: "GET",
  });

  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorMessage(res));
  }

  return res.json() as Promise<ResumeDetail>;
}

export function resumeDetailPath(resumeId: string): string {
  return `/resume/${encodeURIComponent(resumeId)}`;
}
