"use client";

import { Video, FileOutput, Upload } from "lucide-react";

import { useCurrentUser } from "@/hooks/use-auth";
import { useVideos } from "@/hooks/use-videos";
import { useUIStore } from "@/stores/ui-store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { VideoCard } from "@/components/videos/video-card";

export default function DashboardPage() {
  const { data: user } = useCurrentUser();
  const { data, isLoading } = useVideos(0, 5);
  const { setUploadDialogOpen } = useUIStore();

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div>
        <h1 className="text-2xl font-bold text-white">
          Welcome back{user?.email ? `, ${user.email.split("@")[0]}` : ""}
        </h1>
        <p className="text-slate-400">
          Here&apos;s what&apos;s happening with your videos
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="border-slate-800 bg-slate-900/60">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">
              Total Videos
            </CardTitle>
            <Video className="h-4 w-4 text-indigo-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {isLoading ? (
                <Skeleton className="h-8 w-12" />
              ) : (
                data?.total ?? 0
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/60">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">
              Completed
            </CardTitle>
            <FileOutput className="h-4 w-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {isLoading ? (
                <Skeleton className="h-8 w-12" />
              ) : (
                data?.videos.filter((v) => v.status === "completed").length ?? 0
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/60 sm:col-span-2 lg:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">
              Quick Action
            </CardTitle>
            <Upload className="h-4 w-4 text-purple-400" />
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => setUploadDialogOpen(true)}
              variant="outline"
              className="w-full border-slate-700 text-slate-300 hover:bg-slate-800"
              size="sm"
            >
              Upload New Video
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent videos */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-white">
          Recent Videos
        </h2>
        {isLoading ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-lg" />
            ))}
          </div>
        ) : data?.videos.length === 0 ? (
          <Card className="border-slate-800 bg-slate-900/40 border-dashed">
            <CardContent className="flex flex-col items-center gap-3 py-10">
              <Video className="h-10 w-10 text-slate-600" />
              <p className="text-sm text-slate-500">No videos yet</p>
              <Button
                onClick={() => setUploadDialogOpen(true)}
                size="sm"
                className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white"
              >
                Upload your first video
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {data?.videos.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
