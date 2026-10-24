import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { Mail } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import AuthFrame from "@/components/auth/AuthFrame";
import { apiRequest } from "@/api/kairos-client";

const ForgotPassword = () => {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    setMessage("");
    setError("");
    setIsSubmitting(true);
    const form = new FormData(formElement);
    const email = String(form.get("email") ?? "").trim().toLowerCase();

    try {
      const result = await apiRequest<{ message: string }>("/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setMessage(result.message);
      formElement.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to request a password reset. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthFrame
      asideEyebrow="Account recovery"
      asideTitle="Back to your work, without compromising security."
      asideDescription="Request a single-use reset link for the email address associated with your Kairos account."
      footer={<>Remember your password? <Link to="/auth/auth2/login" className="font-medium text-foreground underline underline-offset-4 hover:text-muted-foreground">Sign in</Link></>}
    >
      <div className="mb-7">
        <div className="mb-5 flex size-11 items-center justify-center rounded-md border bg-muted"><Mail className="size-5" /></div>
        <p className="text-sm font-medium text-muted-foreground">ACCOUNT RECOVERY</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Reset your password</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">Enter your account email. If it’s eligible, we’ll send a reset link that expires in 30 minutes.</p>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="email">Email address</Label>
          <Input id="email" name="email" type="email" autoComplete="email" autoCapitalize="none" spellCheck={false} maxLength={255} placeholder="you@institution.edu" required className="h-11" />
        </div>
        {message && <Alert><AlertDescription>{message}</AlertDescription></Alert>}
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Sending request…" : "Send reset link"}
        </Button>
        <p className="text-center text-xs leading-5 text-muted-foreground">For privacy, we use the same response whether or not an eligible account exists.</p>
      </form>
    </AuthFrame>
  );
};

export default ForgotPassword;
