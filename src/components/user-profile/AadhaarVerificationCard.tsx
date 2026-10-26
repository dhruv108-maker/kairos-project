import { useCallback, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Clock3, RefreshCw, ShieldCheck } from "lucide-react";

import { apiRequest, ApiError } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type VerificationStatus = {
  id?: string | null;
  status: "not_started" | "pending" | "verified" | "failed" | "expired" | "cancelled" | "review_required";
  /** Legacy identity-only alias; use identity_verified for UI decisions. */
  verified?: boolean;
  email_verified: boolean;
  identity_verified: boolean;
  identity_verification_status: VerificationStatus["status"];
  available: boolean;
  provider: string;
  created_at?: string | null;
  updated_at?: string | null;
  expires_at?: string | null;
  completed_at?: string | null;
  error_category?: string | null;
  message?: string | null;
  declared_name?: string | null;
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
  const [declaredName, setDeclaredName] = useState("");
  const [aadhaarNumber, setAadhaarNumber] = useState("");
  const [detailsConsent, setDetailsConsent] = useState(false);
  const [verificationConsent, setVerificationConsent] = useState(false);
  const [savingDetails, setSavingDetails] = useState(false);
  const [starting, setStarting] = useState(false);
  const [notice, setNotice] = useState("");

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
      setDeclaredName(current.declared_name ?? "");
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

  const verified = status?.identity_verified === true && status.status === "verified";
  const completedAt = displayDate(status?.completed_at);

  const saveDetails = async () => {
    setSavingDetails(true);
    setError("");
    setNotice("");
    try {
      await apiRequest("/identity-verification/details", {
        method: "PUT",
        body: JSON.stringify({
          declared_name: declaredName.trim() || null,
          consent: detailsConsent,
          consent_notice_version: "aadhaar-optional-v1",
        }),
      });
      await refresh(true);
      setNotice("Your optional name was saved. It is user-declared, not a verified identity claim.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "We couldn't save your optional details.");
    } finally {
      setSavingDetails(false);
    }
  };

  const startVerification = async () => {
    setStarting(true);
    setError("");
    setNotice("");
    try {
      const result = await apiRequest<{ status: "verified" | "failed"; verified: boolean; message?: string | null }>("/identity-verification/initiate", {
        method: "POST",
        body: JSON.stringify({
          aadhaar_number: aadhaarNumber,
          consent: verificationConsent,
          consent_notice_version: "aadhaar-online-v1",
        }),
      });
      await refresh(true);
      setNotice(result.verified ? "Aadhaar verification succeeded. Kairos has saved the provider-confirmed result." : "The provider could not verify these details. No verified status was recorded.");
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 503) {
        setNotice("Online Aadhaar verification is not configured or the provider is temporarily unavailable. No verified status was recorded.");
      } else {
        setError(cause instanceof Error ? cause.message : "We couldn't start verification.");
      }
    } finally {
      setAadhaarNumber("");
      setStarting(false);
    }
  };

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
                  {status.status === "not_started" ? "Not started" : status.status.replace(/_/g, " ")}
                </Badge>
              )}
            </div>
            <CardDescription className="mt-1">
              Optional identity step. You can skip it and continue using Kairos normally.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3 rounded-lg border p-4">
          <div className="space-y-1">
            <Label htmlFor="identity-declared-name">Name for identity workflow (optional)</Label>
            <Input id="identity-declared-name" value={declaredName} maxLength={200} autoComplete="name" onChange={(event) => setDeclaredName(event.target.value)} placeholder="Enter a name only if you want to" />
            <p className="text-xs text-muted-foreground">This is user-provided, not a verified claim. No Aadhaar number, OTP, or document is collected here.</p>
          </div>
          <div className="flex items-start gap-2">
            <Checkbox id="identity-details-consent" checked={detailsConsent} onCheckedChange={(checked) => setDetailsConsent(checked === true)} />
            <Label htmlFor="identity-details-consent" className="text-sm leading-5 font-normal">I consent to storing this optional name for the identity workflow.</Label>
          </div>
          <Button type="button" variant="outline" onClick={() => void saveDetails()} disabled={savingDetails || !detailsConsent}>{savingDetails ? "Saving…" : "Save optional details"}</Button>
        </div>
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
                Online verification is handled server-side by Signzy when the provider account is configured and enabled. Kairos never treats document OCR or a client-supplied result as verification.
              </p>
              {!status?.available && (
                <p className="text-muted-foreground">
                  The provider integration is not enabled for this deployment yet. Ask the Kairos administrator to configure the provider credentials and enable the integration.
                </p>
              )}
              <p className="text-muted-foreground">
                Your Aadhaar number is sent to the configured verification provider for this request and is not saved in Kairos. You can skip this optional workflow.
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
        {notice && <p role="status" className="rounded-md border p-3 text-sm">{notice}</p>}
        <div className="space-y-3 border-t pt-4">
          <div className="space-y-1">
            <Label htmlFor="aadhaar-online-number">Aadhaar number</Label>
            <Input
              id="aadhaar-online-number"
              type="password"
              inputMode="numeric"
              autoComplete="off"
              maxLength={12}
              value={aadhaarNumber}
              onChange={(event) => setAadhaarNumber(event.target.value.replace(/\D/g, "").slice(0, 12))}
              placeholder="Enter 12-digit Aadhaar number"
              aria-describedby="aadhaar-online-number-help"
            />
            <p id="aadhaar-online-number-help" className="text-xs leading-5 text-muted-foreground">
              Used only for this provider request. Do not enter it unless you have reviewed and agree to the consent below.
            </p>
          </div>
          <div className="flex items-start gap-2">
            <Checkbox id="identity-verification-consent" checked={verificationConsent} onCheckedChange={(checked) => setVerificationConsent(checked === true)} />
            <Label htmlFor="identity-verification-consent" className="text-sm leading-5 font-normal">I explicitly consent to sending my Aadhaar number to Signzy for online verification, subject to applicable provider privacy and retention terms.</Label>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-xl text-xs leading-5 text-muted-foreground">
            Status is retrieved from the authenticated Kairos API. This page never sets a verification result locally.
          </p>
          <div className="flex flex-wrap gap-2">
          <Button type="button" onClick={() => void startVerification()} disabled={!verificationConsent || starting || !/^\d{12}$/.test(aadhaarNumber)}>{starting ? "Verifying securely…" : "Verify Aadhaar online"}</Button>
          <Button type="button" variant="outline" onClick={() => void refresh(true)} disabled={loading || refreshing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />
            {refreshing ? "Refreshing…" : "Refresh status"}
          </Button>
          </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
