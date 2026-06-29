/**
 * api.ts
 * ------
 * Typed fetch wrapper for the PDF Protector backend REST API.
 * All functions throw on non-2xx responses with a descriptive message.
 */

import type {
  CleanupResponse,
  ProcessRequest,
  StatusResponse,
  UploadResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

/** Upload PDFs and Excel file; returns job ID */
export async function uploadFiles(
  pdfs: File[],
  excel: File
): Promise<UploadResponse> {
  const form = new FormData();
  pdfs.forEach((f) => form.append("pdfs", f));
  form.append("excel", excel);

  const res = await fetch(`${BASE_URL}/api/v1/upload`, {
    method: "POST",
    body: form,
  });
  return handleResponse<UploadResponse>(res);
}

/** Start encryption for a job (returns 202) */
export async function processJob(
  jobId: string,
  options: ProcessRequest = {}
): Promise<{ job_id: string; status: string; message: string }> {
  const res = await fetch(`${BASE_URL}/api/v1/process/${jobId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      skip_encrypted: options.skip_encrypted ?? true,
      overwrite: options.overwrite ?? true,
      max_workers: options.max_workers ?? 4,
    }),
  });
  return handleResponse(res);
}

/** Poll job status */
export async function getStatus(jobId: string): Promise<StatusResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/status/${jobId}`);
  return handleResponse<StatusResponse>(res);
}

/** Returns a download URL for the encrypted ZIP */
export function getDownloadUrl(jobId: string): string {
  return `${BASE_URL}/api/v1/download/${jobId}`;
}

/** Manually clean up a job */
export async function cleanupJob(jobId: string): Promise<CleanupResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/cleanup/${jobId}`, {
    method: "DELETE",
  });
  return handleResponse<CleanupResponse>(res);
}
