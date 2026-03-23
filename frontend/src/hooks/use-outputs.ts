"use client";

// =============================================================================
// Output hooks powered by TanStack Query
// =============================================================================

import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, ApiClientError } from "@/lib/api-client";
import type { OutputListResponse, DownloadUrlResponse } from "@/types/api";

/** Fetch outputs for a video */
export function useOutputs(videoId: string) {
  return useQuery<OutputListResponse>({
    queryKey: ["outputs", videoId],
    queryFn: () =>
      api.get<OutputListResponse>(`/outputs?video_id=${videoId}`),
    enabled: !!videoId,
  });
}

/** Get signed download URL and open in new tab */
export function useDownloadOutput() {
  return useMutation({
    mutationFn: (outputId: string) =>
      api.get<DownloadUrlResponse>(`/outputs/${outputId}/download-url`),
    onSuccess: (data) => {
      window.open(data.download_url, "_blank");
    },
    onError: (err: ApiClientError) => {
      toast.error(err.detail || "Download failed");
    },
  });
}
