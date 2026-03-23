// =============================================================================
// TypeScript types mirroring backend Pydantic schemas
// =============================================================================

// --- Auth Types ---
export interface User {
  id: string;
  email: string;
  is_email_verified: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface EmailTokenRequest {
  token: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

export interface MessageResponse {
  message: string;
  detail?: string;
}

// --- Video Types ---
export interface Video {
  id: string;
  original_filename: string | null;
  duration: number | null;
  file_size_bytes: number | null;
  status: VideoStatus;
  created_at: string;
}

export type VideoStatus = "uploaded" | "processing" | "completed" | "failed";

export interface VideoListResponse {
  videos: Video[];
  total: number;
}

export interface VideoUploadResponse {
  id: string;
  original_filename: string;
  file_size_bytes: number;
  status: string;
  message: string;
}

// --- Job Types ---
export interface Job {
  id: string;
  video_id: string;
  status: JobStatus;
  progress: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export type JobStatus = "queued" | "processing" | "completed" | "failed" | "cancelled";

export interface JobStartRequest {
  video_id: string;
}

export interface JobStartResponse {
  id: string;
  video_id: string;
  status: string;
  message: string;
}

export interface JobCancelResponse {
  id: string;
  video_id: string;
  status: string;
  message: string;
}

// --- Output Types ---
export interface Output {
  id: string;
  video_id: string;
  resolution: string | null;
  duration: number | null;
  file_size_bytes: number | null;
  created_at: string;
}

export interface OutputListResponse {
  outputs: Output[];
  total: number;
}

export interface DownloadUrlResponse {
  download_url: string;
  expires_in: number;
}

// --- SSE Progress Event ---
export interface ProgressEvent {
  job_id: string;
  status: JobStatus;
  progress: number;
  step?: string;
}

// --- API Error ---
export interface ApiError {
  detail: string;
}
