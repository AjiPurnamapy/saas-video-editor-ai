"use client";

import Link from "next/link";
import { MoreVertical, Trash2, Eye, FileVideo } from "lucide-react";

import type { Video } from "@/types/api";
import { useDeleteVideo } from "@/hooks/use-videos";
import { StatusBadge } from "@/components/videos/status-badge";
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/** Format bytes */
function formatBytes(bytes: number | null): string {
  if (!bytes) return "—";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/** Format date */
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function VideoCard({ video }: { video: Video }) {
  const deleteVideo = useDeleteVideo();

  return (
    <Card className="group border-slate-800 bg-slate-900/60 transition-all hover:border-slate-700 hover:bg-slate-900/80">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-800">
            <FileVideo className="h-5 w-5 text-indigo-400" />
          </div>
          <div className="min-w-0 flex-1">
            <Link
              href={`/dashboard/videos/${video.id}`}
              className="block truncate text-sm font-medium text-white hover:text-indigo-400 transition-colors"
            >
              {video.original_filename || "Untitled Video"}
            </Link>
            <p className="text-xs text-slate-500">{formatDate(video.created_at)}</p>
          </div>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger
            className="h-8 w-8 text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-md hover:bg-slate-800"
          >
            <MoreVertical className="h-4 w-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="border-slate-800 bg-slate-900"
          >
            <DropdownMenuItem className="cursor-pointer">
              <Link href={`/dashboard/videos/${video.id}`} className="flex items-center w-full">
                <Eye className="mr-2 h-4 w-4" />
                View Details
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => deleteVideo.mutate(video.id)}
              className="text-red-400 focus:bg-red-500/10 focus:text-red-400 cursor-pointer"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>

      <CardContent>
        <div className="flex items-center gap-2">
          <StatusBadge status={video.status} />
          <span className="text-xs text-slate-500">
            {formatBytes(video.file_size_bytes)}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
