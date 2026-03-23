"use client";

// =============================================================================
// Job hooks powered by TanStack Query
// =============================================================================

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, ApiClientError } from "@/lib/api-client";
import type {
  Job,
  JobStartRequest,
  JobStartResponse,
  JobCancelResponse,
} from "@/types/api";

const jobKeys = {
  all: ["jobs"] as const,
  detail: (id: string) => [...jobKeys.all, "detail", id] as const,
};

/** Fetch single job */
export function useJob(id: string) {
  return useQuery<Job>({
    queryKey: jobKeys.detail(id),
    queryFn: () => api.get<Job>(`/jobs/${id}`),
    enabled: !!id,
    refetchInterval: (query) => {
      const job = query.state.data;
      // Auto-poll while job is active
      if (job && (job.status === "queued" || job.status === "processing")) {
        return 3000;
      }
      return false;
    },
  });
}

/** Start processing job */
export function useStartJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: JobStartRequest) =>
      api.post<JobStartResponse>("/jobs/start", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      toast.success("Processing started!");
    },
    onError: (err: ApiClientError) => {
      toast.error(err.detail || "Failed to start processing");
    },
  });
}

/** Cancel job */
export function useCancelJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) =>
      api.post<JobCancelResponse>(`/jobs/${jobId}/cancel`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobKeys.all });
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      toast.success("Processing cancelled");
    },
    onError: (err: ApiClientError) => {
      toast.error(err.detail || "Cancel failed");
    },
  });
}
