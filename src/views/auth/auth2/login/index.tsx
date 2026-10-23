import { useState, type FormEvent } from "react";
import { Card } from "@/components/ui/card";
import { Link, useNavigate } from "react-router";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import FullLogo from "src/layouts/full/shared/logo/FullLogo";
import { useAuth } from "@/context/auth/AuthContext";

const BoxedLogin = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");

    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-accent px-4 py-10">
      <Card className="w-full max-w-md border-none shadow-lg p-6 sm:p-8">
        <div className="mx-auto w-fit"><FullLogo /></div>
        <div className="mt-6 mb-7 text-center">
          <p className="text-2xl font-semibold tracking-tight text-foreground">Welcome to Kairos</p>
          <p className="mt-2 text-sm text-muted-foreground">Sign in to your academic workspace</p>
        </div>

        <form className="space-y-5 w-full" onSubmit={handleSubmit}>
          <div className="space-y-1.5">
            <Label htmlFor="email" className="text-sm font-medium">Institutional email</Label>
            <Input id="email" name="email" type="email" autoComplete="username" placeholder="you@institution.edu" required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password" className="text-sm font-medium">Password</Label>
            <Input id="password" name="password" type="password" autoComplete="current-password" placeholder="Enter your password" required />
          </div>

          {error && (
            <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="flex justify-end">
            <Link to="/auth/auth2/forgot-password" className="text-sm font-medium text-primary hover:underline">
              Forgot password?
            </Link>
          </div>

          <Button type="submit" size="lg" className="w-full rounded-lg" disabled={isSubmitting}>
            {isSubmitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <div className="mt-6 text-center text-sm text-muted-foreground">
          Need access? Contact your institution administrator.
        </div>
      </Card>
    </div>
  );
};

export default BoxedLogin;
