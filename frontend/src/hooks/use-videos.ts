"use client";

// =============================================================================
// Video hooks powered by TanStack Query
// =============================================================================

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, ApiClientError } from "@/lib/api-client";
import type {
  Video,
  VideoListResponse,
  VideoUploadResponse,
} from "@/types/api";

/** Query key factory */
const videoKeys = {
  all: ["videos"] as const,
  list: (skip: number, limit: number) => [...videoKeys.all, "list", skip, limit] as const,
  detail: (id: string) => [...videoKeys.all, "detail", id] as const,
};

/** Fetch paginated video list */
export function useVideos(skip = 0, limit = 10) {
  return useQuery<VideoListResponse>({
    queryKey: videoKeys.list(skip, limit),
    queryFn: () => api.get<VideoListResponse>(`/videos?skip=${skip}&limit=${limit}`),
  });
}

/** Fetch single video */
export function useVideo(id: string) {
  return useQuery<Video>({
    queryKey: videoKeys.detail(id),
    queryFn: () => api.get<Video>(`/videos/${id}`),
    enabled: !!id,
  });
}

/** Upload video mutation */
export function useUploadVideo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      file,
      onProgress,
    }: {
      file: File;
      onProgress?: (percent: number) => void;
    }) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.upload<VideoUploadResponse>("/videos/upload", formData, onProgress);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: videoKeys.all });
      toast.success(`"${data.original_filename}" uploaded successfully`);
    },
    onError: (err: ApiClientError) => {
      toast.error(err.detail || "Upload failed");
    },
  });
}

/** Delete video mutation */
export function useDeleteVideo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/videos/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoKeys.all });
      toast.success("Video deleted");
    },
    onError: (err: ApiClientError) => {
      toast.error(err.detail || "Delete failed");
    },
  });
}
