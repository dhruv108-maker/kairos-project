import { useEffect, useState } from "react";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { Link } from "react-router";

import { apiRequest } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { getAadhaarBannerContent, type AadhaarBannerStatus } from "./aadhaar-verification-banner-state.mjs";

type VerificationStatusResponse = AadhaarBannerStatus & {
  email_verified: boolean;
  identity_verified: boolean;
  identity_verification_status: AadhaarBannerStatus["status"];
  available?: boolean;
  provider?: string;
  declared_name?: string | null;
};

export default function AadhaarVerificationBanner() {
  const { account } = useAuth();
  const isStudent = account?.roles.some((role) => role.toUpperCase() === "STUDENT") ?? false;
  const [status, setStatus] = useState<AadhaarBannerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let active = true;

    if (!isStudent) {
      setLoading(false);
      setStatus(null);
      return () => {
        active = false;
      };
    }

    setLoading(true);
    setUnavailable(false);

    apiRequest<VerificationStatusResponse | null>("/identity-verification/status", {
      method: "GET",
      cache: "no-store",
    })
      .then((current) => {
        if (!active) return;
        // A missing identity record is the normal not-started state.
        setStatus(current ?? { status: "not_started", identity_verified: false });
      })
      .catch(() => {
        if (!active) return;
        // Do not guess at a user's status when the authoritative request fails.
        // The banner is non-blocking; the profile page exposes its own retry/error UI.
        setUnavailable(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [isStudent, account?.id]);

  if (!isStudent || loading || unavailable) return null;

  const content = getAadhaarBannerContent(status);
  if (!content) return null;

  return (
    <section
      aria-labelledby="aadhaar-verification-banner-title"
      className="flex flex-col gap-4 rounded-xl border border-border/80 bg-muted/30 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5"
    >
      <div className="flex min-w-0 items-start gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-primary/15 bg-primary/5 text-primary">
          <ShieldCheck className="size-5" aria-hidden="true" />
        </div>
        <div className="min-w-0 space-y-1">
          <h2 id="aadhaar-verification-banner-title" className="text-sm font-semibold text-foreground sm:text-base">
            {content.title}
          </h2>
          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
            {content.description}
          </p>
        </div>
      </div>
      <Link
        to="/student/profile"
        aria-label={content.action}
        className="inline-flex min-h-9 shrink-0 items-center justify-center gap-2 self-start rounded-lg bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground outline-none transition-colors hover:bg-primary/90 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:self-center"
      >
        {content.action}
        <ArrowRight className="size-4" aria-hidden="true" />
      </Link>
    </section>
  );
}
