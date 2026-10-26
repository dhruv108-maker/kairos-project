import { useCallback, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Clock3, RefreshCw, ShieldCheck, UploadCloud } from "lucide-react";

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
  verified?: boolean;
  email_verified: boolean;
  identity_verified: boolean;
  identity_verification_status: VerificationStatus["status"];
  available: boolean;
  ocr_available: boolean;
  provider: string;
  created_at?: string | null;
  updated_at?: string | null;
  expires_at?: string | null;
  completed_at?: string | null;
  error_category?: string | null;
  message?: string | null;
  declared_name?: string | null;
};

type AadhaarOcrResult = {
  success: boolean;
  document_type: string;
  fields: Record<string, string | null>;
  processing_time_ms?: number | null;
  identity_verified: false;
  message: string;
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
  const [detailsConsent, setDetailsConsent] = useState(false);
  const [ocrConsent, setOcrConsent] = useState(false);
  const [savingDetails, setSavingDetails] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [document, setDocument] = useState<File | null>(null);
  const [ocrResult, setOcrResult] = useState<AadhaarOcrResult | null>(null);
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
          ? "Your session has expired. Sign in again to check status."
          : "We couldn't retrieve your identity status. Check your connection and try again.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (account?.roles.some((role) => role.toUpperCase() === "STUDENT")) void refresh();
    else setLoading(false);
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

  const extractDocument = async () => {
    if (!document) return;
    setExtracting(true);
    setError("");
    setNotice("");
    setOcrResult(null);
    try {
      const body = new FormData();
      body.append("file", document);
      body.append("consent", "true");
      const result = await apiRequest<AadhaarOcrResult>("/identity-verification/ocr", {
        method: "POST",
        body,
      });
      setOcrResult(result);
      setNotice("Document text extracted successfully. Identity verification is a separate step and remains unavailable in this workflow.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "We couldn't extract document details.");
    } finally {
      setDocument(null);
      const picker = window.document.getElementById("aadhaar-ocr-file") as HTMLInputElement | null;
      if (picker) picker.value = "";
      setExtracting(false);
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
              <CardTitle id="aadhaar-verification-title">Aadhaar document extraction</CardTitle>
              {verified && <Badge>Verified</Badge>}
              {!loading && status && !verified && <Badge variant="outline">{status.status === "not_started" ? "Unverified" : status.status.replace(/_/g, " ")}</Badge>}
            </div>
            <CardDescription className="mt-1">
              Verifico currently provides document OCR here, not identity verification. Extracted details cannot change your verification status.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3 rounded-lg border p-4">
          <div className="space-y-1">
            <Label htmlFor="identity-declared-name">Name for identity workflow (optional)</Label>
            <Input id="identity-declared-name" value={declaredName} maxLength={200} autoComplete="name" onChange={(event) => setDeclaredName(event.target.value)} placeholder="Enter a name only if you want to" />
            <p className="text-xs text-muted-foreground">This name is user-provided, not a verified claim.</p>
          </div>
          <div className="flex items-start gap-2">
            <Checkbox id="identity-details-consent" checked={detailsConsent} onCheckedChange={(checked) => setDetailsConsent(checked === true)} />
            <Label htmlFor="identity-details-consent" className="text-sm leading-5 font-normal">I consent to storing this optional name for the identity workflow.</Label>
          </div>
          <Button type="button" variant="outline" onClick={() => void saveDetails()} disabled={savingDetails || !detailsConsent}>{savingDetails ? "Saving…" : "Save optional details"}</Button>
        </div>

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground" role="status"><RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />Checking identity status…</div>
        ) : error ? (
          <div role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /><span>{error}</span></div>
        ) : verified ? (
          <div className="flex items-start gap-2 rounded-lg border border-emerald-700/20 bg-emerald-50/70 p-3 text-sm text-emerald-950 dark:bg-emerald-950/20 dark:text-emerald-100" role="status">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <div><p className="font-medium">Your identity verification is recorded as complete.</p>{completedAt && <p className="mt-1">Completed {completedAt}</p>}</div>
          </div>
        ) : (
          <div className="flex items-start gap-2 rounded-lg border p-3 text-sm" role="status">
            <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <div className="space-y-1">
              <p className="font-medium">Identity verification is not available in this workflow</p>
              <p className="text-muted-foreground">Your document was read successfully, but OCR only copies information from the document. It does not authenticate the Aadhaar, confirm ownership, or verify your identity.</p>
              <p className="text-muted-foreground">{status?.message ?? "Kairos needs a separate supported, authoritative identity-verification provider before it can mark an account as verified."}</p>
              {!status?.ocr_available && <p className="text-muted-foreground">Document OCR is not configured or is temporarily unavailable. Configure the private VERIFICO_API key on the backend.</p>}
            </div>
          </div>
        )}

        <div className="space-y-3 border-t pt-4">
          <div className="space-y-1">
            <Label htmlFor="aadhaar-ocr-file">Aadhaar document (JPG, PNG, or PDF; up to 10 MB)</Label>
            <Input
              id="aadhaar-ocr-file"
              type="file"
              accept="image/jpeg,image/png,application/pdf,.jpg,.jpeg,.png,.pdf"
              onChange={(event) => { setDocument(event.target.files?.[0] ?? null); setOcrResult(null); }}
            />
            <p className="text-xs leading-5 text-muted-foreground">Your document is sent to Verifico for this request only. Kairos does not save the file or raw OCR response. Avoid uploading a document unless you consent to this processing.</p>
          </div>
          <div className="flex items-start gap-2">
            <Checkbox id="identity-ocr-consent" checked={ocrConsent} onCheckedChange={(checked) => setOcrConsent(checked === true)} />
            <Label htmlFor="identity-ocr-consent" className="text-sm leading-5 font-normal">I consent to sending this Aadhaar document to Verifico for OCR extraction. I understand this does not verify my identity.</Label>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="max-w-xl text-xs leading-5 text-muted-foreground">OCR results are shown only for this session and are not saved to Kairos. Extracting them will not verify your identity.</p>
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={() => void extractDocument()} disabled={!document || !ocrConsent || extracting || document.size > 10 * 1024 * 1024}>
                <UploadCloud className="mr-2 h-4 w-4" aria-hidden="true" />{extracting ? "Extracting…" : "Extract document details"}
              </Button>
              <Button type="button" variant="outline" onClick={() => void refresh(true)} disabled={loading || refreshing}><RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />{refreshing ? "Refreshing…" : "Refresh status"}</Button>
            </div>
          </div>
        </div>

        {ocrResult && (
          <section className="space-y-3 rounded-lg border p-4" aria-label="Extracted Aadhaar details">
            <div><h3 className="font-medium">Document details extracted — not verified</h3><p className="text-sm text-muted-foreground">These are OCR results only. They are not proof of identity and cannot be used to mark your Kairos account verified.</p></div>
            <dl className="grid gap-3 sm:grid-cols-2">
              {Object.entries(ocrResult.fields).filter(([key, value]) => value && key !== "aadhaar_last4").map(([key, value]) => (
                <div key={key} className="min-w-0"><dt className="text-xs text-muted-foreground">{key.replace(/_/g, " ")}</dt><dd className="break-words text-sm">{value}</dd></div>
              ))}
              {ocrResult.fields.aadhaar_last4 && <div><dt className="text-xs text-muted-foreground">Aadhaar ending</dt><dd className="text-sm">•••• •••• {ocrResult.fields.aadhaar_last4}</dd></div>}
            </dl>
            <p className="text-xs text-muted-foreground">{ocrResult.message}{ocrResult.processing_time_ms != null ? ` Processing time: ${ocrResult.processing_time_ms} ms.` : ""}</p>
          </section>
        )}

        {notice && <p role="status" className="rounded-md border p-3 text-sm">{notice}</p>}
      </CardContent>
    </Card>
  );
}
