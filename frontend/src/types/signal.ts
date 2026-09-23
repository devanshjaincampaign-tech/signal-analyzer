export interface IngestionMetadata {
  sample_rate?: number;
  num_samples?: number;
  duration_s?: number;
  format?: string;
  is_complex?: boolean;
  channels?: number;
  file_size_bytes?: number;
  [key: string]: any;
}

export type JobStatus = 'uploaded' | 'validated' | 'analyzing' | 'completed' | 'error';

export interface Job {
  job_id: string;
  filename: string;
  file_type: string;
  status: JobStatus;
  error_message?: string | null;
  metadata?: IngestionMetadata | null;
  created_at?: string;
}

export interface SpectralFeatures {
  center_frequency_hz: number;
  bandwidth_hz: number;
  noise_floor_db: number;
  peak_power_db: number;
  sample_rate_used: number;
  sample_rate_was_assumed: boolean;
  spectrogram?: SpectrogramData;
}

export interface SpectrogramData {
  freq_bins: number[];
  time_bins: number[];
  power_db_matrix: number[][];
}

export interface SymbolRateResult {
  samples_per_symbol: number | null;
  symbol_rate_baud: number | null;
  confidence: number;
  method?: string;
  timing_metric?: number;
  [key: string]: any;
}

export interface ModulationCandidate {
  label: string;
  score: number;
}

export interface ClassificationFeatures {
  applicable: boolean;
  envelope_variance?: number;
  inst_freq_variance?: number;
  c42_cumulant?: number;
  reason?: string;
}

export interface ClassificationResult {
  modulation: 'PSK' | 'FSK' | 'QAM' | string | null;
  confidence: number;
  candidates: ModulationCandidate[];
  features_used?: ClassificationFeatures;
  reason?: string;
}

export interface DemodResult {
  success: boolean;
  type?: 'bits' | 'symbol_levels';
  bits?: number[];
  num_bits?: number;
  i_levels?: number[];
  q_levels?: number[];
  reason?: string;
}

export interface InterleavingResult {
  success: boolean;
  stride?: number;
  depth?: number;
  deinterleaved_bits?: number[];
  confidence?: number;
  reason?: string;
}

export interface AnalysisResponse {
  job_id: string;
  features: SpectralFeatures;
  symbol_rate: SymbolRateResult;
  classification: ClassificationResult;
  demod: DemodResult;
  interleaving: InterleavingResult;
}

export interface StoredAnalysisStageRow {
  stage: 'features' | 'symbol_rate' | 'classification' | 'demod' | 'interleaving';
  result_data: any;
  created_at: string;
}

export type ColormapTheme = 'turbo' | 'viridis' | 'inferno' | 'plasma' | 'matrix' | 'cyan';
