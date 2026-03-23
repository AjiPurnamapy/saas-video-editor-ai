"use client";

// =============================================================================
// SSE Job Progress Hook
// =============================================================================
// Connects to GET /api/jobs/{job_id}/progress via EventSource API.
// Returns real-time progress, status, step info, and connection state.

import { useEffect, useRef, useState, useCallback } from "react";
import type { ProgressEvent, JobStatus } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface UseJobProgressOptions {
  /** Only connect when true (e.g., job is queued/processing) */
  enabled?: boolean;
  /** Called when job reaches terminal state */
  onComplete?: (status: JobStatus) => void;
}

interface UseJobProgressReturn {
  /** Progress percentage (0-100) */
  progress: number;
  /** Current job status */
  status: JobStatus | null;
  /** Current processing step name */
  step: string | null;
  /** Whether SSE is connected */
  isConnected: boolean;
  /** Connection error (if any) */
  error: string | null;
}

/**
 * Custom hook that connects to the SSE progress endpoint.
 * 
 * Usage:
 * ```tsx
 * const { progress, status, step, isConnected } = useJobProgress(jobId, {
 *   enabled: job?.status === "processing",
 *   onComplete: () => queryClient.invalidateQueries(["videos"]),
 * });
 * ```
 */
export function useJobProgress(
  jobId: string | null,
  options: UseJobProgressOptions = {}
): UseJobProgressReturn {
  const { enabled = true, onComplete } = options;
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [step, setStep] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const onCompleteRef = useRef(onComplete);

  // Keep callback ref up to date
  onCompleteRef.current = onComplete;

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (!jobId || !enabled) {
      cleanup();
      return;
    }

    const url = `${API_BASE_URL}/jobs/${jobId}/progress`;
    const es = new EventSource(url, { withCredentials: true });
    eventSourceRef.current = es;

    // Connected event
    es.addEventListener("connected", () => {
      setIsConnected(true);
      setError(null);
    });

    // Progress event
    es.addEventListener("progress", (event) => {
      try {
        const data: ProgressEvent = JSON.parse(event.data);
        setProgress(data.progress ?? 0);
        setStatus(data.status);
        if (data.step) setStep(data.step);

        // Terminal statuses close the stream
        const terminal: JobStatus[] = ["completed", "failed", "cancelled"];
        if (terminal.includes(data.status)) {
          cleanup();
          onCompleteRef.current?.(data.status);
        }
      } catch {
        // Ignore parse errors
      }
    });

    // Heartbeat — just confirms connection is alive
    es.addEventListener("heartbeat", () => {
      setIsConnected(true);
    });

    // Connection error
    es.onerror = () => {
      setError("Connection lost. Retrying...");
      setIsConnected(false);
      // EventSource auto-reconnects by default
    };

    return cleanup;
  }, [jobId, enabled, cleanup]);

  return { progress, status, step, isConnected, error };
}
