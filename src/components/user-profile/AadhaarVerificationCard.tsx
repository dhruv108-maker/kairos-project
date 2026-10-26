import { useCallback, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Clock3, RefreshCw, ShieldCheck } from "lucide-react";

import { apiRequest, ApiError } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type VerificationStatus = {
  id?: string | null;
  status: "not_started" | "pending" | "verified" | "failed" | "expired" | "cancelled" | "review_required";
  verified: boolean;
  available: boolean;
  provider: string;
  created_at?: string | null;
  updated_at?: string | null;
  expires_at?: string | null;
  completed_at?: string | null;
  error_category?: string | null;
  message?: string | null;
};

function displayDate(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleString();
}

export default function AadhaarVerificationCard() {
  const { account } = useAuth();
  const [status, setStatus] = useState<VerificationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const current = await apiRequest<VerificationStatus>("/identity-verification/status", {
        method: "GET",
        cache: "no-store",
      });
      setStatus(current);
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.status === 401
          ? "Your session has expired. Sign in again to check verification status."
          : "We couldn't retrieve your verification status. Check your connection and try again.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (account?.roles.some((role) => role.toUpperCase() === "STUDENT")) {
      void refresh();
    } else {
      setLoading(false);
    }
  }, [account, refresh]);

  if (!account?.roles.some((role) => role.toUpperCase() === "STUDENT")) return null;

  const verified = status?.status === "verified" && status.verified === true;
  const completedAt = displayDate(status?.completed_at);

  return (
    <Card className="shadow-none" aria-labelledby="aadhaar-verification-title">
      <CardHeader>
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border bg-muted/40">
            <ShieldCheck className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle id="aadhaar-verification-title">Aadhaar identity verification</CardTitle>
              {verified && <Badge>Verified</Badge>}
              {!loading && status && !verified && (
                <Badge variant="outline">
                  {status.status === "not_started" ? "Not started" : status.status.replaceAll("_", " ")}
                </Badge>
              )}
            </div>
            <CardDescription className="mt-1">
              Check whether an approved identity-verification workflow is available for your account.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
            <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />
            Checking your verification status…
          </div>
        ) : error ? (
          <div role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
        ) : verified ? (
          <div className="flex items-start gap-2 rounded-lg border border-emerald-700/20 bg-emerald-50/70 p-3 text-sm text-emerald-950 dark:bg-emerald-950/20 dark:text-emerald-100" role="status">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <div>
              <p className="font-medium">Your identity verification is recorded as complete.</p>
              {completedAt && <p className="mt-1">Completed {completedAt}</p>}
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-2 rounded-lg border p-3 text-sm" role="status">
            <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <div className="space-y-2">
              <p className="font-medium">Verification is temporarily unavailable.</p>
              <p className="text-muted-foreground">
                The configured Verifico service currently documents Aadhaar document text extraction (OCR), not Aadhaar identity verification against an authoritative source. Kairos will not treat OCR as proof of identity.
              </p>
              <p className="text-muted-foreground">
                No Aadhaar number, OTP, or identity document is requested or uploaded here. Your account remains usable without this optional workflow.
              </p>
            </div>
          </div>
        )}
        {status?.status === "pending" && !verified && (
          <p className="text-sm text-muted-foreground">A verification attempt is pending. Refresh the status before taking further action.</p>
        )}
        {status?.status === "expired" && (
          <p className="text-sm text-muted-foreground">The previous attempt expired. A new attempt cannot be started until an approved provider workflow is configured.</p>
        )}
        {status?.status === "failed" || status?.status === "cancelled" || status?.status === "review_required" ? (
          <p className="text-sm text-muted-foreground">The previous attempt needs attention. Kairos cannot restart or resolve it until a supported provider workflow is available.</p>
        ) : null}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
          <p className="max-w-xl text-xs leading-5 text-muted-foreground">
            Status is retrieved from the authenticated Kairos API. This page never sets a verification result locally.
          </p>
          <Button type="button" variant="outline" onClick={() => void refresh(true)} disabled={loading || refreshing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />
            {refreshing ? "Refreshing…" : "Refresh status"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
