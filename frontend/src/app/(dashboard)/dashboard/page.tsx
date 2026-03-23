"use client";

import { useCurrentUser } from "@/hooks/use-auth";

/**
 * Dashboard page — placeholder for Phase 2.
 * Shows a simple welcome message to verify auth flow works.
 */
export default function DashboardPage() {
  const { data: user } = useCurrentUser();

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold text-white">
          Welcome to ClipForge AI
        </h1>
        <p className="text-slate-400">
          Logged in as <span className="text-indigo-400">{user?.email}</span>
        </p>
        <p className="text-sm text-slate-500">
          Dashboard will be built in Phase 2.
        </p>
      </div>
    </div>
  );
}
