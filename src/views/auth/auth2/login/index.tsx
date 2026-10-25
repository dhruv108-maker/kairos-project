import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import AuthFrame from "@/components/auth/AuthFrame";
import { useAuth } from "@/context/auth/AuthContext";

const BoxedLogin = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) return;
    setError("");
    setIsSubmitting(true);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim().toLowerCase();
    const password = String(form.get("password") ?? "");

    try {
      await login(email, password);
      const state = location.state as { from?: unknown } | null;
      // Only accept same-origin absolute paths. A value such as //evil.example
      // also starts with "/" but is a protocol-relative external URL.
      const destination = typeof state?.from === "string"
        && state.from.startsWith("/")
        && !state.from.startsWith("//")
        ? state.from
        : "/";
      navigate(destination, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in. Please check your details and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthFrame
      asideEyebrow="Your academic workspace"
      asideTitle="Your academic future, in focus."
      asideDescription=""
      footer={<>New to Kairos? <Link to="/onboarding" className="font-medium text-foreground underline underline-offset-4 hover:text-muted-foreground">Create an account</Link></>}
    >
      <div className="mb-8 min-w-0">
        <p className="text-sm font-medium text-muted-foreground">WELCOME BACK</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight">Sign in to Kairos</h2>
        
      </div>

      <form className="min-w-0 space-y-5" onSubmit={handleSubmit}>
        <div className="min-w-0 space-y-2">
          <Label htmlFor="email">Email address</Label>
          <div className="relative min-w-0">
            <Mail aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              placeholder="you@institution.edu"
              maxLength={255}
              required
              aria-describedby="email-hint"
              className="pl-10"
            />
          </div>
          <p id="email-hint" className="text-xs leading-5 text-muted-foreground">Enter the email address you used to register.</p>
        </div>

        <div className="min-w-0 space-y-2">
          <div className="flex min-w-0 flex-wrap items-center justify-between gap-x-3 gap-y-1">
            <Label htmlFor="password">Password</Label>
            <Link to="/auth/auth2/forgot-password" className="text-sm font-medium underline underline-offset-4 hover:text-muted-foreground">Forgot password?</Link>
          </div>
          <div className="relative min-w-0">
            <LockKeyhole aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              placeholder="Enter your password"
              required
              aria-describedby={error ? "signin-error" : undefined}
              className="pl-10 pr-12"
            />
            <button
              type="button"
              onClick={() => setShowPassword((value) => !value)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
              className="absolute right-1.5 top-1/2 inline-flex size-9 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground outline-none hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
            >
              {showPassword ? <EyeOff aria-hidden="true" className="size-4" /> : <Eye aria-hidden="true" className="size-4" />}
            </button>
          </div>
        </div>

        {error && (
          <Alert id="signin-error" variant="destructive" role="alert" aria-live="polite" className="min-w-0 break-words">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Button type="submit" size="lg" className="h-11 w-full whitespace-normal" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Sign in"}
          {!isSubmitting && <ArrowRight aria-hidden="true" className="ml-2 size-4" />}
        </Button>
        <p className="text-center text-xs leading-5 text-muted-foreground">Your account access follows your institution’s permissions and verification requirements.</p>
      </form>
    </AuthFrame>
  );
};

export default BoxedLogin;
