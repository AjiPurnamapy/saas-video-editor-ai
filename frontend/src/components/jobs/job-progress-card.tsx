"use client";

import { Loader2, Wifi, WifiOff, XCircle } from "lucide-react";

import { useJobProgress } from "@/hooks/use-job-progress";
import { useCancelJob } from "@/hooks/use-jobs";
import { StatusBadge } from "@/components/videos/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { JobStatus } from "@/types/api";

interface JobProgressCardProps {
  jobId: string;
  /** Only connect SSE when job is active */
  isActive: boolean;
  /** Called when job reaches terminal state */
  onComplete?: (status: JobStatus) => void;
}

export function JobProgressCard({
  jobId,
  isActive,
  onComplete,
}: JobProgressCardProps) {
  const { progress, status, step, isConnected, error } = useJobProgress(
    jobId,
    { enabled: isActive, onComplete }
  );
  const cancelJob = useCancelJob();

  return (
    <Card className="border-slate-800 bg-slate-900/60">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="text-sm font-medium text-slate-300">
          Processing
        </CardTitle>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <Wifi className="h-3.5 w-3.5 text-emerald-400" />
          ) : isActive ? (
            <WifiOff className="h-3.5 w-3.5 text-amber-400" />
          ) : null}
          {status && <StatusBadge status={status} />}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Progress bar */}
        <div className="space-y-1.5">
          <Progress
            value={progress}
            className="h-2.5"
          />
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500">
              {step || "Initializing..."}
            </span>
            <span className="font-mono text-slate-400">{progress}%</span>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <p className="flex items-center gap-1.5 text-xs text-amber-400">
            <WifiOff className="h-3 w-3" />
            {error}
          </p>
        )}

        {/* Cancel button — only when actively processing */}
        {isActive && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => cancelJob.mutate(jobId)}
            disabled={cancelJob.isPending}
            className="w-full border-red-500/30 text-red-400 hover:bg-red-500/10"
          >
            {cancelJob.isPending ? (
              <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
            ) : (
              <XCircle className="mr-2 h-3.5 w-3.5" />
            )}
            Cancel Processing
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
