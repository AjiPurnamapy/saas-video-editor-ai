"use client";

import { useState } from "react";
import { Plus, Video } from "lucide-react";

import { useVideos } from "@/hooks/use-videos";
import { useUIStore } from "@/stores/ui-store";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { VideoCard } from "@/components/videos/video-card";

const PAGE_SIZE = 10;

export default function VideosPage() {
  const [page, setPage] = useState(0);
  const skip = page * PAGE_SIZE;
  const { data, isLoading } = useVideos(skip, PAGE_SIZE);
  const { setUploadDialogOpen } = useUIStore();

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">My Videos</h1>
          <p className="text-sm text-slate-400">
            {data ? `${data.total} video${data.total !== 1 ? "s" : ""}` : "Loading..."}
          </p>
        </div>
        <Button
          onClick={() => setUploadDialogOpen(true)}
          className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500"
          size="sm"
        >
          <Plus className="mr-1.5 h-4 w-4" />
          Upload
        </Button>
      </div>

      {/* Video grid */}
      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-lg" />
          ))}
        </div>
      ) : data?.videos.length === 0 ? (
        <Card className="border-slate-800 bg-slate-900/40 border-dashed">
          <CardContent className="flex flex-col items-center gap-3 py-16">
            <Video className="h-12 w-12 text-slate-600" />
            <p className="text-slate-400 font-medium">No videos uploaded yet</p>
            <p className="text-sm text-slate-500">
              Upload your first video to get started
            </p>
            <Button
              onClick={() => setUploadDialogOpen(true)}
              className="mt-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white"
            >
              <Plus className="mr-1.5 h-4 w-4" />
              Upload Video
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data?.videos.map((video) => (
            <VideoCard key={video.id} video={video} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="border-slate-700 text-slate-300 hover:bg-slate-800"
          >
            Previous
          </Button>
          <span className="text-sm text-slate-500">
            Page {page + 1} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="border-slate-700 text-slate-300 hover:bg-slate-800"
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
