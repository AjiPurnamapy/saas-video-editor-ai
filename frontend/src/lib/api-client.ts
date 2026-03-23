// =============================================================================
// API Client — fetch wrapper with cookie credentials and error handling
// =============================================================================

import type { ApiError } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

/**
 * Custom error class for API errors.
 * Carries the HTTP status code and server error message.
 */
export class ApiClientError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiClientError";
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Core fetch wrapper with:
 * - credentials: "include" for cookie-based auth
 * - Automatic JSON Content-Type for non-FormData bodies
 * - Error response parsing into ApiClientError
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const isFormData = options.body instanceof FormData;

  const headers: HeadersInit = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...((options.headers as Record<string, string>) || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include", // Send cookies (session_id, csrf)
  });

  // Handle 204 No Content (e.g. DELETE responses)
  if (response.status === 204) {
    return undefined as T;
  }

  // Parse response body
  let data: T | ApiError;
  try {
    data = await response.json();
  } catch {
    throw new ApiClientError(response.status, "Invalid server response");
  }

  // Throw on error status
  if (!response.ok) {
    const errorData = data as ApiError;
    throw new ApiClientError(
      response.status,
      errorData.detail || `Request failed (${response.status})`
    );
  }

  return data as T;
}

// =============================================================================
// Convenience methods
// =============================================================================

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: "GET" }),

  post: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  put: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  delete: <T>(endpoint: string) => request<T>(endpoint, { method: "DELETE" }),

  /**
   * Upload a file via multipart/form-data.
   * Supports progress tracking via XMLHttpRequest.
   */
  upload: <T>(
    endpoint: string,
    formData: FormData,
    onProgress?: (percent: number) => void
  ): Promise<T> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE_URL}${endpoint}`);
      xhr.withCredentials = true;

      if (onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            onProgress(Math.round((event.loaded / event.total) * 100));
          }
        };
      }

      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText);
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(data as T);
          } else {
            reject(new ApiClientError(xhr.status, data.detail || "Upload failed"));
          }
        } catch {
          reject(new ApiClientError(xhr.status, "Invalid response"));
        }
      };

      xhr.onerror = () => reject(new ApiClientError(0, "Network error"));
      xhr.send(formData);
    });
  },
};
