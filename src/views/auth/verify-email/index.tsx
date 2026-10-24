import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { CheckCircle2, MailCheck } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import AuthFrame from "@/components/auth/AuthFrame";
import { apiRequest } from "@/api/kairos-client";

const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [verified, setVerified] = useState(false);

  const verify = async () => {
    if (!token || isVerifying) return;
    setError("");
    setMessage("");
    setIsVerifying(true);
    try {
      const result = await apiRequest<{ message: string }>("/auth/verify-email", {
        method: "POST",
        body: JSON.stringify({ token }),
      });
      setMessage(result.message);
      setVerified(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "This verification link is invalid or expired. Request a new one below.");
    } finally {
      setIsVerifying(false);
    }
  };

  const resend = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setMessage("");
    setIsResending(true);
    try {
      const result = await apiRequest<{ message: string }>("/auth/verification/resend", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to request another verification email.");
    } finally {
      setIsResending(false);
    }
  };

  return (
    <AuthFrame
      asideEyebrow="Account verification"
      asideTitle="A verified email keeps your academic identity secure."
      asideDescription="Confirm that you can access the email address linked to your Kairos account before signing in."
      footer={<>Already verified? <Link to="/auth/auth2/login" className="font-medium text-foreground underline underline-offset-4 hover:text-muted-foreground">Sign in</Link></>}
    >
      <div className="mb-7">
        <div className="mb-5 flex size-11 items-center justify-center rounded-md border bg-muted">
          {verified ? <CheckCircle2 className="size-5" /> : <MailCheck className="size-5" />}
        </div>
        <p className="text-sm font-medium text-muted-foreground">EMAIL VERIFICATION</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">{verified ? "Email confirmed" : "Verify your email"}</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {verified ? "Your email address has been verified. You can now continue to sign in if your account is active." : "Use the secure link from your Kairos verification email. The link expires after 30 minutes."}
        </p>
      </div>

      {message && <Alert className="mb-5"><AlertTitle>Update</AlertTitle><AlertDescription>{message}</AlertDescription></Alert>}
      {error && <Alert variant="destructive" className="mb-5"><AlertDescription>{error}</AlertDescription></Alert>}

      {!verified && token && (
        <Button type="button" size="lg" className="w-full" onClick={verify} disabled={isVerifying}>
          {isVerifying ? "Verifying email…" : "Confirm email address"}
        </Button>
      )}

      {!verified && (
        <div className="mt-7 border-t pt-6">
          <h2 className="text-sm font-medium">Need a new verification link?</h2>
          <p className="mt-1 text-sm leading-5 text-muted-foreground">Enter the address you registered with. For privacy, the response won’t reveal whether an account exists.</p>
          <form className="mt-4 space-y-3" onSubmit={resend}>
            <div className="space-y-2">
              <Label htmlFor="email">Email address</Label>
              <Input id="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@institution.edu" required maxLength={255} />
            </div>
            <Button type="submit" variant="outline" className="w-full" disabled={isResending}>
              {isResending ? "Requesting link…" : "Resend verification email"}
            </Button>
          </form>
        </div>
      )}

      {verified && <Button className="mt-2 w-full" onClick={() => { window.location.href = "/auth/auth2/login"; }}>Continue to sign in</Button>}
    </AuthFrame>
  );
};

export default VerifyEmail;
