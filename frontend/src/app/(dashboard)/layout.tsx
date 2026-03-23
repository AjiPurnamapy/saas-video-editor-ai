"use client";

import { AuthGuard } from "@/components/auth-guard";

/**
 * Dashboard layout — wraps all /dashboard/* routes with AuthGuard.
 * Phase 2 will add sidebar and top bar here.
 */
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <main className="flex-1">{children}</main>
    </AuthGuard>
  );
}
