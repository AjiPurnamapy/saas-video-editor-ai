"use client";

// =============================================================================
// Auth hooks powered by TanStack Query
// =============================================================================

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { api, ApiClientError } from "@/lib/api-client";
import type {
  User,
  LoginRequest,
  RegisterRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  EmailTokenRequest,
  MessageResponse,
} from "@/types/api";

/** Query key for the current user */
const USER_KEY = ["auth", "me"];

/**
 * Fetch the current authenticated user.
 * Returns null if not authenticated (401).
 */
export function useCurrentUser() {
  return useQuery<User | null>({
    queryKey: USER_KEY,
    queryFn: async () => {
      try {
        return await api.get<User>("/auth/me");
      } catch (err) {
        if (err instanceof ApiClientError && err.status === 401) {
          return null;
        }
        throw err;
      }
    },
    staleTime: 5 * 60 * 1000, // 5 min
    retry: false,
  });
}

/** Login mutation */
export function useLogin() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (data: LoginRequest) => api.post<User>("/auth/login", data),
    onSuccess: (user) => {
      queryClient.setQueryData(USER_KEY, user);
      toast.success("Welcome back!");
      router.push("/dashboard");
    },
    onError: (err: ApiClientError) => {
      toast.error(err.detail || "Login failed");
    },
  });
}

/** Register mutation */
export function useRegister() {
  const router = useRouter();

  return useMutation({
    mutationFn: (data: RegisterRequest) =>
      api.post<User>("/auth/register", data),
    onSuccess: () => {
      toast.success("Account created! Check your email to verify.");
      router.push("/login");
    },
    onError: (err: ApiClientError) => {
      toast.error(err.detail || "Registration failed");
    },
  });
}

/** Logout mutation */
export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: () => api.post<MessageResponse>("/auth/logout"),
    onSuccess: () => {
      queryClient.setQueryData(USER_KEY, null);
      queryClient.clear();
      toast.success("Logged out");
      router.push("/login");
    },
  });
}

/** Forgot password mutation */
export function useForgotPassword() {
  return useMutation({
    mutationFn: (data: ForgotPasswordRequest) =>
      api.post<MessageResponse>("/auth/forgot-password", data),
    onSuccess: () => {
      toast.success("If that email exists, a reset link was sent.");
    },
    onError: (err: ApiClientError) => {
      toast.error(err.detail || "Request failed");
    },
  });
}

/** Reset password mutation */
export function useResetPassword() {
  const router = useRouter();

  return useMutation({
    mutationFn: (data: ResetPasswordRequest) =>
      api.post<MessageResponse>("/auth/reset-password", data),
    onSuccess: () => {
      toast.success("Password reset! Please log in.");
      router.push("/login");
    },
    onError: (err: ApiClientError) => {
      toast.error(err.detail || "Reset failed");
    },
  });
}

/** Verify email mutation */
export function useVerifyEmail() {
  return useMutation({
    mutationFn: (data: EmailTokenRequest) =>
      api.post<MessageResponse>("/auth/verify-email", data),
    onSuccess: () => {
      toast.success("Email verified!");
    },
    onError: (err: ApiClientError) => {
      toast.error(err.detail || "Verification failed");
    },
  });
}
