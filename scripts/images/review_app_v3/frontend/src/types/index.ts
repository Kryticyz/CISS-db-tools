// Species types
export interface SpeciesInfo {
  name: string;
  image_count: number;
  has_embeddings: boolean;
  processed?: boolean;
  duplicate_count?: number;
  similar_count?: number;
  outlier_count?: number;
}

export interface SpeciesSummary {
  species: SpeciesInfo[];
  total_species: number;
  total_images: number;
  species_with_issues: number;
  faiss_available: boolean;
  cnn_available: boolean;
}

export interface AppStatus {
  faiss_available: boolean;
  faiss_vector_count?: number;
  cnn_available: boolean;
  base_dir: string;
  embeddings_dir: string;
  species_count: number;
}

// Analysis types
export interface ImageInfo {
  filename: string;
  path: string;
  size: number;
  hash?: string;
}

export interface DuplicateGroup {
  group_id: number;
  keep: ImageInfo;
  duplicates: ImageInfo[];
  total_in_group: number;
}

export interface DuplicateResult {
  species_name: string;
  total_images: number;
  hashed_images: number;
  duplicate_groups: DuplicateGroup[];
  total_duplicates: number;
  hash_size: number;
  hamming_threshold: number;
}

export interface SimilarGroup {
  group_id: number;
  images: ImageInfo[];
  count: number;
  avg_similarity?: number;
}

export interface SimilarityResult {
  species_name: string;
  total_images: number;
  processed_images: number;
  similar_groups: SimilarGroup[];
  total_in_groups: number;
  similarity_threshold: number;
  model_name: string;
  from_faiss: boolean;
}

export interface OutlierInfo {
  filename: string;
  path: string;
  size: number;
  distance_to_centroid: number;
  z_score?: number;
}

export interface OutlierResult {
  species_name: string;
  total_images: number;
  outliers: OutlierInfo[];
  outlier_count: number;
  threshold_percentile: number;
  computed_threshold: number;
  mean_distance: number;
  std_distance: number;
}

export interface CombinedAnalysis {
  species_name: string;
  duplicates: DuplicateResult;
  similar: SimilarityResult;
  outliers: OutlierResult;
}

// Parameter types
export interface AnalysisParameters {
  hash_size: number;
  hamming_threshold: number;
  similarity_threshold: number;
  threshold_percentile: number;
}

export interface ParameterInfo {
  name: string;
  label: string;
  description: string;
  type: 'int' | 'float';
  min: number;
  max: number;
  default: number;
  step: number;
}

export interface ParametersResponse {
  parameters: ParameterInfo[];
  current: AnalysisParameters;
}

// Deletion types
export type DeletionReason = 'duplicate' | 'similar' | 'outlier' | 'manual';

export interface QueuedFile {
  species: string;
  filename: string;
  path: string;
  reason: DeletionReason;
  added_at: string;
  size: number;
  thumbnail_path?: string;
}

export interface DeletionQueue {
  files: QueuedFile[];
  total_count: number;
  total_size: number;
  total_size_human: string;
  by_species: Record<string, number>;
  by_reason: Record<string, number>;
}

export interface DeletionPreview {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  species_affected: string[];
  by_reason: Record<string, number>;
  warnings: string[];
}

export interface DeletionResult {
  success: boolean;
  deleted_count: number;
  deleted_files: string[];
  failed_count: number;
  failed_files: Array<{ path: string; error: string }>;
  affected_species: string[];
}

// Utility function to calculate total issues
export function getTotalIssues(species: SpeciesInfo): number {
  return (
    (species.duplicate_count ?? 0) +
    (species.similar_count ?? 0) +
    (species.outlier_count ?? 0)
  );
}

// Get status color based on issue count
export function getStatusColor(issues: number): string {
  if (issues === 0) return 'status-clean';
  if (issues <= 10) return 'status-warning';
  return 'status-danger';
}
