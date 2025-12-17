/**
 * Type-safe API client for the review application.
 */

import type {
  SpeciesSummary,
  AppStatus,
  DuplicateResult,
  SimilarityResult,
  OutlierResult,
  CombinedAnalysis,
  ParametersResponse,
  DeletionQueue,
  DeletionPreview,
  DeletionResult,
  DeletionReason,
} from '../types';

// API error type
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// Generic fetch wrapper with error handling
async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // Ignore JSON parse errors
    }
    throw new ApiError(response.status, response.statusText, message);
  }

  return response.json();
}

// Build URL with query parameters
function buildUrl(path: string, params?: Record<string, string | number | boolean>): string {
  if (!params) return path;
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  }
  const queryString = searchParams.toString();
  return queryString ? `${path}?${queryString}` : path;
}

// API client
export const api = {
  // Dashboard endpoints
  dashboard: {
    summary: () => fetchJson<SpeciesSummary>('/api/dashboard/summary'),
    status: () => fetchJson<AppStatus>('/api/dashboard/status'),
  },

  // Analysis endpoints
  analysis: {
    parameters: () => fetchJson<ParametersResponse>('/api/analysis/parameters'),

    duplicates: (
      species: string,
      params?: { hash_size?: number; hamming_threshold?: number }
    ) =>
      fetchJson<DuplicateResult>(
        buildUrl(`/api/analysis/duplicates/${encodeURIComponent(species)}`, params)
      ),

    similar: (species: string, params?: { similarity_threshold?: number }) =>
      fetchJson<SimilarityResult>(
        buildUrl(`/api/analysis/similar/${encodeURIComponent(species)}`, params)
      ),

    outliers: (species: string, params?: { threshold_percentile?: number }) =>
      fetchJson<OutlierResult>(
        buildUrl(`/api/analysis/outliers/${encodeURIComponent(species)}`, params)
      ),

    combined: (
      species: string,
      params?: {
        hash_size?: number;
        hamming_threshold?: number;
        similarity_threshold?: number;
        threshold_percentile?: number;
      }
    ) =>
      fetchJson<CombinedAnalysis>(
        buildUrl(`/api/analysis/combined/${encodeURIComponent(species)}`, params)
      ),
  },

  // Image endpoints
  images: {
    url: (species: string, filename: string) =>
      `/api/images/${encodeURIComponent(species)}/${encodeURIComponent(filename)}`,
  },

  // Deletion endpoints
  deletion: {
    getQueue: () => fetchJson<DeletionQueue>('/api/deletion/queue'),

    addToQueue: (
      files: Array<{ species: string; filename: string; size?: number }>,
      reason: DeletionReason
    ) =>
      fetchJson<{ added: number; total: number }>('/api/deletion/queue', {
        method: 'POST',
        body: JSON.stringify({ files, reason }),
      }),

    removeFromQueue: (species: string, filename: string) =>
      fetchJson<{ removed: boolean; path: string }>(
        `/api/deletion/queue/${encodeURIComponent(species)}/${encodeURIComponent(filename)}`,
        { method: 'DELETE' }
      ),

    clearQueue: () =>
      fetchJson<{ cleared: number }>('/api/deletion/queue/clear', {
        method: 'POST',
      }),

    preview: () => fetchJson<DeletionPreview>('/api/deletion/preview'),

    confirm: () =>
      fetchJson<DeletionResult>('/api/deletion/confirm', {
        method: 'POST',
      }),

    markComplete: (species: string) =>
      fetchJson<{ success: boolean; species: string; newly_marked: boolean }>(
        `/api/deletion/mark-complete/${encodeURIComponent(species)}`,
        { method: 'POST' }
      ),
  },

  // Health check
  health: () => fetchJson<{ status: string }>('/api/health'),
};
