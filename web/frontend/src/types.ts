export interface ChannelMetrics {
  rms_uv: number;
  ptp_uv: number;
  max_abs_uv: number;
  mean_uv: number;
}

export interface ExpectedChannel {
  canonical: string;
  matched_name: string | null;
  found: boolean;
  metrics: ChannelMetrics | null;
}

export interface MarkerEvent {
  onset_s: number;
  label: string;
  source: string;
}

export interface RecordingSummary {
  n_channels: number | null;
  channel_names: string[];
  sfreq_hz: number | null;
  duration_s: number | null;
  n_samples: number | null;
  n_annotations: number | null;
  highpass_hz: number | null;
  lowpass_hz: number | null;
  meas_date: string | null;
}

export interface AnalysisSummary {
  status: string;
  config_name: string;
  unit_assumption: string;
  recording: RecordingSummary;
  expected_channels: ExpectedChannel[];
  markers: {
    n_events: number | null;
    distinct_labels: string[];
    candidate_marker_channels: string[];
    events: MarkerEvent[];
  };
}

export interface GitStatus {
  enabled: boolean;
  committed: boolean;
  pushed: boolean;
  commit_sha: string | null;
  commit_url: string | null;
  branch: string | null;
  message: string;
  error: string | null;
  steps: string[];
}

export interface SessionMeta {
  session_id: string;
  date: string;
  original_filename: string;
  extension: string;
  format_label: string;
  analysis_mode: 'analyze' | 'catalog-only' | 'archival-only';
  size_bytes: number;
  sha256: string;
  uploaded_at: string;
  raw_relpath: string;
  analysis_status: string;
  analysis: AnalysisSummary | null;
  report_relpaths: string[];
  warnings: string[];
  hard_failures: string[];
  git: GitStatus | null;
}

export interface AcceptedFormat {
  ext: string;
  label: string;
  mode: string;
}

export interface HealthStatus {
  status: string;
  version: string;
  config_available: boolean;
  max_upload_bytes: number;
  max_upload_mb: number;
  accepted_formats: AcceptedFormat[];
}

export interface RepoSyncStatus {
  enabled: boolean;
  branch: string;
  remote: string;
  remote_url: string | null;
  credentials_available: boolean;
  ahead: number | null;
  note: string;
}

export interface DemoResponse {
  diagnostic: any;
  artifacts: Record<string, string>;
}
