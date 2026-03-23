import { redirect } from "next/navigation";

/**
 * Root page — redirects to dashboard (or login if not authenticated).
 * The AuthGuard in the dashboard layout handles the auth check.
 */
export default function HomePage() {
  redirect("/dashboard");
}
