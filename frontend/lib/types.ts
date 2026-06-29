// Shared TypeScript types matching the FastAPI Pydantic schemas

export type JobStatus = "pending" | "processing" | "completed" | "failed";

export interface UploadResponse {
  job_id: string;
  file_count: number;
  excel_filename: string;
  message: string;
}

export interface ProcessRequest {
  skip_encrypted?: boolean;
  overwrite?: boolean;
  max_workers?: number;
}

export interface FileResult {
  filename: string;
  status: "success" | "missing" | "failed" | "skipped";
  message: string;
  elapsed_ms: number;
}

export interface JobStats {
  total: number;
  success: number;
  missing: number;
  failed: number;
  skipped: number;
  elapsed_sec: number;
}

export interface StatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;       // 0–100
  done: number;
  total: number;
  stats: JobStats;
  error?: string | null;
  created_at: string;
  completed_at?: string | null;
  results: FileResult[];
}

export interface CleanupResponse {
  job_id: string;
  message: string;
}
