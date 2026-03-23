"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

import { useVerifyEmail } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function VerifyEmailPage() {
  const [token, setToken] = useState("");
  const verify = useVerifyEmail();

  // S-05: Read token from URL fragment (#token=...) — NOT query param
  useEffect(() => {
    const hash = window.location.hash;
    const match = hash.match(/token=([^&]+)/);
    if (match) {
      const t = decodeURIComponent(match[1]);
      setToken(t);
      verify.mutate({ token: t });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Card className="border-slate-800 bg-slate-900/80 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="text-2xl font-bold text-white text-center">
          Email Verification
        </CardTitle>
      </CardHeader>

      <CardContent className="flex flex-col items-center gap-4 py-6">
        {!token && (
          <>
            <XCircle className="h-12 w-12 text-red-400" />
            <p className="text-slate-400 text-center">
              Invalid or missing verification token.
            </p>
          </>
        )}

        {token && verify.isPending && (
          <>
            <Loader2 className="h-12 w-12 animate-spin text-indigo-400" />
            <p className="text-slate-400">Verifying your email...</p>
          </>
        )}

        {token && verify.isSuccess && (
          <>
            <CheckCircle2 className="h-12 w-12 text-emerald-400" />
            <p className="text-emerald-300 font-medium">
              Email verified successfully!
            </p>
            <Link href="/login">
              <Button className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500">
                Continue to sign in
              </Button>
            </Link>
          </>
        )}

        {token && verify.isError && (
          <>
            <XCircle className="h-12 w-12 text-red-400" />
            <p className="text-red-300">
              Verification failed. The token may be expired.
            </p>
            <Link href="/login">
              <Button
                variant="outline"
                className="border-slate-700 text-slate-300 hover:bg-slate-800"
              >
                Go to sign in
              </Button>
            </Link>
          </>
        )}
      </CardContent>
    </Card>
  );
}
