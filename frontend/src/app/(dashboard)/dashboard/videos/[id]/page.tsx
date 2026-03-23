"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  FileVideo,
  Play,
  Trash2,
  Download,
  Loader2,
  XCircle,
} from "lucide-react";

import { useVideo, useDeleteVideo } from "@/hooks/use-videos";
import { useStartJob, useCancelJob, useJob } from "@/hooks/use-jobs";
import { useOutputs, useDownloadOutput } from "@/hooks/use-outputs";
import { StatusBadge } from "@/components/videos/status-badge";
import { JobProgressCard } from "@/components/jobs/job-progress-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useRouter } from "next/navigation";

function formatBytes(bytes: number | null): string {
  if (!bytes) return "—";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function VideoDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { data: video, isLoading } = useVideo(id);
  const deleteVideo = useDeleteVideo();
  const startJob = useStartJob();
  const { data: outputsData } = useOutputs(id);
  const downloadOutput = useDownloadOutput();
  const queryClient = useQueryClient();

  // Track the latest job ID from startJob response
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const isJobActive = video?.status === "processing";

  // Find latest job (if any) — we'll need a separate endpoint for this later
  // For now, use the video status to determine action

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 rounded-lg" />
      </div>
    );
  }

  if (!video) {
    return (
      <div className="flex flex-col items-center gap-4 py-20">
        <p className="text-slate-400">Video not found</p>
        <Link href="/dashboard/videos">
          <Button variant="outline" className="border-slate-700 text-slate-300">
            Back to Videos
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back + Title */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard/videos">
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 text-slate-400 hover:text-white"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <h1 className="text-xl font-bold text-white">
              {video.original_filename || "Untitled Video"}
            </h1>
            <p className="text-sm text-slate-500">
              {formatDate(video.created_at)}
            </p>
          </div>
        </div>
        <StatusBadge status={video.status} />
      </div>

      {/* Info card */}
      <Card className="border-slate-800 bg-slate-900/60">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-slate-400">
            Video Info
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-xs text-slate-500">File Size</p>
              <p className="text-sm font-medium text-white">
                {formatBytes(video.file_size_bytes)}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Duration</p>
              <p className="text-sm font-medium text-white">
                {video.duration ? `${video.duration.toFixed(1)}s` : "—"}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Status</p>
              <p className="text-sm font-medium text-white capitalize">
                {video.status}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        {video.status === "uploaded" && (
          <Button
            onClick={() =>
              startJob.mutate(
                { video_id: video.id },
                { onSuccess: (data) => setActiveJobId(data.id) }
              )
            }
            disabled={startJob.isPending}
            className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500"
          >
            {startJob.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            Start Processing
          </Button>
        )}

        <Button
          variant="outline"
          onClick={() => {
            deleteVideo.mutate(video.id, {
              onSuccess: () => router.push("/dashboard/videos"),
            });
          }}
          disabled={deleteVideo.isPending}
          className="border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300"
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Delete Video
        </Button>
      </div>

      {/* SSE Progress Card — shown when job is active */}
      {(isJobActive || activeJobId) && (
        <JobProgressCard
          jobId={activeJobId || ""}
          isActive={isJobActive}
          onComplete={() => {
            queryClient.invalidateQueries({ queryKey: ["videos"] });
            queryClient.invalidateQueries({ queryKey: ["outputs", id] });
            setActiveJobId(null);
          }}
        />
      )}

      <Separator className="bg-slate-800" />

      {/* Outputs */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-white">
          Outputs
          {outputsData && (
            <span className="ml-2 text-sm font-normal text-slate-500">
              ({outputsData.total})
            </span>
          )}
        </h2>

        {!outputsData || outputsData.outputs.length === 0 ? (
          <Card className="border-slate-800 bg-slate-900/40 border-dashed">
            <CardContent className="flex flex-col items-center gap-2 py-8">
              <FileVideo className="h-8 w-8 text-slate-600" />
              <p className="text-sm text-slate-500">
                No outputs yet. Start processing to generate outputs.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {outputsData.outputs.map((output) => (
              <Card
                key={output.id}
                className="border-slate-800 bg-slate-900/60"
              >
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10">
                      <FileVideo className="h-5 w-5 text-emerald-400" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">
                        {output.resolution || "Output"}
                      </p>
                      <p className="text-xs text-slate-500">
                        {formatBytes(output.file_size_bytes)}
                      </p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => downloadOutput.mutate(output.id)}
                    disabled={downloadOutput.isPending}
                    className="border-slate-700 text-slate-300 hover:bg-slate-800"
                  >
                    <Download className="mr-1.5 h-3.5 w-3.5" />
                    Download
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
