import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { CheckCircle2, Eye, EyeOff, LockKeyhole } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import AuthFrame from "@/components/auth/AuthFrame";
import { apiRequest } from "@/api/kairos-client";

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    setError("");
    setMessage("");
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? "");
    const confirmPassword = String(form.get("confirm_password") ?? "");

    if (!token) {
      setError("This password reset link is missing its token. Request a new link.");
      return;
    }
    if (password.length < 12 || password.length > 128) {
      setError("Choose a password between 12 and 128 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("The passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await apiRequest<{ message: string }>("/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ token, new_password: password }),
      });
      setMessage(result.message);
      formElement.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset your password. Request a new link and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthFrame
      asideEyebrow="Account recovery"
      asideTitle="Get back to your academic work, securely."
      asideDescription="Choose a new password to protect your Kairos account. Reset links are single-use and expire after 30 minutes."
      footer={<>Remember your password? <Link to="/auth/auth2/login" className="font-medium text-foreground underline underline-offset-4 hover:text-muted-foreground">Sign in</Link></>}
    >
      <div className="mb-7">
        <div className="mb-5 flex size-11 items-center justify-center rounded-md border bg-muted"><LockKeyhole className="size-5" /></div>
        <p className="text-sm font-medium text-muted-foreground">PASSWORD RESET</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Create a new password</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">Use at least 12 characters. You’ll need to sign in again after the reset.</p>
      </div>

      {message ? (
        <div className="space-y-4">
          <Alert><CheckCircle2 className="size-4" /><AlertDescription>{message}</AlertDescription></Alert>
          <Button className="w-full" onClick={() => { window.location.href = "/auth/auth2/login"; }}>Continue to sign in</Button>
        </div>
      ) : (
        <form className="space-y-4" onSubmit={submit}>
          {!token && <Alert variant="destructive"><AlertDescription>This link has no reset token. Request a fresh password reset email.</AlertDescription></Alert>}
          <div className="space-y-2">
            <Label htmlFor="password">New password</Label>
            <div className="relative">
              <Input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={12} maxLength={128} required disabled={!token} className="h-11 pr-11" />
              <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} className="absolute right-2 top-1/2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm_password">Confirm new password</Label>
            <div className="relative">
              <Input id="confirm_password" name="confirm_password" type={showConfirmPassword ? "text" : "password"} autoComplete="new-password" minLength={12} maxLength={128} required disabled={!token} className="h-11 pr-11" />
              <button type="button" onClick={() => setShowConfirmPassword((value) => !value)} aria-label={showConfirmPassword ? "Hide confirmation password" : "Show confirmation password"} aria-pressed={showConfirmPassword} className="absolute right-2 top-1/2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                {showConfirmPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>
          {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
          <Button type="submit" size="lg" className="w-full" disabled={isSubmitting || !token}>
            {isSubmitting ? "Updating password…" : "Reset password"}
          </Button>
          <p className="text-center text-sm text-muted-foreground"><Link to="/auth/auth2/forgot-password" className="underline underline-offset-4 hover:text-foreground">Request a new reset link</Link></p>
        </form>
      )}
    </AuthFrame>
  );
};

export default ResetPassword;
