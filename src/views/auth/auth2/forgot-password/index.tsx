import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import FullLogo from "src/layouts/full/shared/logo/FullLogo";
import { apiRequest } from "@/api/kairos-client";

const BoxedForgotpwd = () => {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage("");
    setError("");
    setIsSubmitting(true);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim().toLowerCase();

    try {
      const result = await apiRequest<{ message: string }>("/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setMessage(result.message);
      event.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to request a password reset. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-muted px-4 py-10">
      <div className="flex min-h-[calc(100vh-5rem)] items-center justify-center">
        <Card className="w-full max-w-md border-none p-6 shadow-lg">
          <div className="mx-auto mb-6 w-fit"><FullLogo /></div>
          <p className="mb-5 text-sm text-muted-foreground">
            Enter the email address associated with your account. If the account is eligible,
            password reset instructions will be sent when email delivery is available.
          </p>
          <form className="w-full space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input id="email" name="email" type="email" autoComplete="email" required />
            </div>
            {message && <p role="status" className="text-sm text-muted-foreground">{message}</p>}
            {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full rounded-lg" disabled={isSubmitting}>
              {isSubmitting ? "Sending request…" : "Request password reset"}
            </Button>
          </form>
          <div className="mt-5 text-center text-sm">
            <Link className="text-primary hover:underline" to="/auth/auth2/login">Back to sign in</Link>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default BoxedForgotpwd;
