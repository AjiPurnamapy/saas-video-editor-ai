"use client";

import { useCallback, useState, useRef } from "react";
import { Upload, X, FileVideo, Loader2 } from "lucide-react";

import { useUploadVideo } from "@/hooks/use-videos";
import { useUIStore } from "@/stores/ui-store";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

/** Format bytes to human-readable size */
function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

const ACCEPTED_EXTENSIONS = ".mp4,.mov,.avi,.mkv,.webm,.mpeg";

export function UploadDialog() {
  const { uploadDialogOpen, setUploadDialogOpen } = useUIStore();
  const uploadVideo = useUploadVideo();
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const reset = useCallback(() => {
    setSelectedFile(null);
    setProgress(0);
    setDragActive(false);
  }, []);

  const handleClose = useCallback(() => {
    if (uploadVideo.isPending) return; // Don't close while uploading
    setUploadDialogOpen(false);
    reset();
  }, [uploadVideo.isPending, setUploadDialogOpen, reset]);

  const handleFile = useCallback((file: File) => {
    setSelectedFile(file);
    setProgress(0);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleUpload = useCallback(() => {
    if (!selectedFile) return;
    uploadVideo.mutate(
      { file: selectedFile, onProgress: setProgress },
      {
        onSuccess: () => {
          handleClose();
        },
      }
    );
  }, [selectedFile, uploadVideo, handleClose]);

  return (
    <Dialog open={uploadDialogOpen} onOpenChange={handleClose}>
      <DialogContent className="border-slate-800 bg-slate-900 sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-white">Upload Video</DialogTitle>
          <DialogDescription className="text-slate-400">
            Drag and drop or select a video file to upload
          </DialogDescription>
        </DialogHeader>

        {/* Drop zone */}
        {!selectedFile && (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 transition-all ${
              dragActive
                ? "border-indigo-500 bg-indigo-500/10"
                : "border-slate-700 bg-slate-800/30 hover:border-slate-600 hover:bg-slate-800/50"
            }`}
          >
            <div className="rounded-full bg-slate-800 p-3">
              <Upload className="h-6 w-6 text-slate-400" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-slate-300">
                Click to browse or drag & drop
              </p>
              <p className="mt-1 text-xs text-slate-500">
                MP4, MOV, AVI, MKV, WebM — max 500MB
              </p>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS}
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
              }}
            />
          </div>
        )}

        {/* Selected file preview */}
        {selectedFile && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-800/50 p-3">
              <FileVideo className="h-8 w-8 text-indigo-400" />
              <div className="flex-1 min-w-0">
                <p className="truncate text-sm font-medium text-white">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-slate-500">
                  {formatBytes(selectedFile.size)}
                </p>
              </div>
              {!uploadVideo.isPending && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-slate-500 hover:text-slate-300"
                  onClick={reset}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>

            {/* Progress bar */}
            {uploadVideo.isPending && (
              <div className="space-y-2">
                <Progress value={progress} className="h-2" />
                <p className="text-center text-xs text-slate-500">
                  Uploading... {progress}%
                </p>
              </div>
            )}

            {/* Upload button */}
            <Button
              onClick={handleUpload}
              disabled={uploadVideo.isPending}
              className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500"
            >
              {uploadVideo.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload
                </>
              )}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
