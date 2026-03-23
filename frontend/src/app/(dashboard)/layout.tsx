"use client";

import { AuthGuard } from "@/components/auth-guard";
import { Sidebar } from "@/components/dashboard/sidebar";
import { Topbar } from "@/components/dashboard/topbar";
import { UploadDialog } from "@/components/videos/upload-dialog";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Topbar />
          <main className="flex-1 overflow-y-auto bg-slate-950 p-4 lg:p-6">
            {children}
          </main>
        </div>
      </div>
      <UploadDialog />
    </AuthGuard>
  );
}
