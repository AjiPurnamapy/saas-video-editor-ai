import { Badge } from "@/components/ui/badge";
import type { VideoStatus, JobStatus } from "@/types/api";

const statusConfig: Record<
  string,
  { label: string; className: string }
> = {
  uploaded: {
    label: "Uploaded",
    className: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  },
  queued: {
    label: "Queued",
    className: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  },
  processing: {
    label: "Processing",
    className: "bg-amber-500/15 text-amber-400 border-amber-500/30 animate-pulse",
  },
  completed: {
    label: "Completed",
    className: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  },
  failed: {
    label: "Failed",
    className: "bg-red-500/15 text-red-400 border-red-500/30",
  },
  cancelled: {
    label: "Cancelled",
    className: "bg-slate-500/15 text-slate-400 border-slate-500/30",
  },
};

export function StatusBadge({ status }: { status: VideoStatus | JobStatus | string }) {
  const config = statusConfig[status] || {
    label: status,
    className: "bg-slate-500/15 text-slate-400 border-slate-500/30",
  };

  return (
    <Badge variant="outline" className={config.className}>
      {config.label}
    </Badge>
  );
}
