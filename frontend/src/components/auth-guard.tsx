"use client";

// =============================================================================
// AuthGuard — redirects unauthenticated users to /login
// =============================================================================

import { useCurrentUser } from "@/hooks/use-auth";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { Loader2 } from "lucide-react";

export function AuthGuard({ children }: { children: ReactNode }) {
  const { data: user, isLoading, isError } = useCurrentUser();
  const router = useRouter();

  useEffect(() => {
    // Redirect to login if: not loading AND (no user OR error fetching user)
    if (!isLoading && (!user || isError)) {
      router.replace("/login");
    }
  }, [user, isLoading, isError, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950">
        <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
      </div>
    );
  }

  if (!user) return null;

  return <>{children}</>;
}
