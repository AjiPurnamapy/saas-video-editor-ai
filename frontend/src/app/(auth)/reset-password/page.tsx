"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Eye, EyeOff, Loader2, Lock, Check, X } from "lucide-react";

import { useResetPassword } from "@/hooks/use-auth";
import { PASSWORD_RULES } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function checkPasswordRules(password: string) {
  return [
    password.length >= 8,
    /[A-Z]/.test(password),
    /[a-z]/.test(password),
    /\d/.test(password),
    /[!@#$%^&*(),.?":{}|<>_\-]/.test(password),
  ];
}

export default function ResetPasswordPage() {
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const reset = useResetPassword();

  const rulesPassed = checkPasswordRules(newPassword);
  const allPassed = rulesPassed.every(Boolean);

  // S-05: Read token from URL fragment (#token=...) — NOT query param
  useEffect(() => {
    const hash = window.location.hash;
    const match = hash.match(/token=([^&]+)/);
    if (match) {
      setToken(decodeURIComponent(match[1]));
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !allPassed) return;
    reset.mutate({ token, new_password: newPassword });
  };

  if (!token) {
    return (
      <Card className="border-slate-800 bg-slate-900/80 backdrop-blur-sm">
        <CardContent className="py-8 text-center">
          <p className="text-slate-400">
            Invalid or missing reset token. Please use the link from your email.
          </p>
          <Link href="/forgot-password">
            <Button
              variant="outline"
              className="mt-4 border-slate-700 text-slate-300 hover:bg-slate-800"
            >
              Request a new link
            </Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-slate-800 bg-slate-900/80 backdrop-blur-sm">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold text-white">
          Reset password
        </CardTitle>
        <CardDescription className="text-slate-400">
          Enter your new password below
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="password" className="text-slate-300">
              New Password
            </Label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                className="border-slate-700 bg-slate-800/50 pl-10 pr-10 text-white placeholder:text-slate-500 focus:border-indigo-500 focus:ring-indigo-500/20"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-3 text-slate-500 hover:text-slate-300"
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>

            {newPassword.length > 0 && (
              <ul className="mt-2 space-y-1">
                {PASSWORD_RULES.map((rule, i) => (
                  <li
                    key={rule}
                    className={`flex items-center gap-2 text-xs transition-colors ${
                      rulesPassed[i] ? "text-emerald-400" : "text-slate-500"
                    }`}
                  >
                    {rulesPassed[i] ? (
                      <Check className="h-3 w-3" />
                    ) : (
                      <X className="h-3 w-3" />
                    )}
                    {rule}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </CardContent>

        <CardFooter>
          <Button
            type="submit"
            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500 shadow-lg shadow-indigo-500/25 transition-all"
            disabled={reset.isPending || !allPassed}
          >
            {reset.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Resetting...
              </>
            ) : (
              "Reset password"
            )}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
