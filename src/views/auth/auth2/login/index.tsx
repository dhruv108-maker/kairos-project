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
    setError("");
    setIsSubmitting(true);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim().toLowerCase();
    const password = String(form.get("password") ?? "");

    try {
      await login(email, password);
      const state = location.state as { from?: unknown } | null;
      const destination = typeof state?.from === "string" && state.from.startsWith("/")
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
      asideTitle="A clearer way to learn, teach, and belong."
      asideDescription="Sign in to continue your work with the people, programmes, and institutions that shape your academic journey."
      footer={<>New to Kairos? <Link to="/onboarding" className="font-medium text-foreground underline underline-offset-4 hover:text-muted-foreground">Create an account</Link></>}
    >
      <div className="mb-8">
        <p className="text-sm font-medium text-muted-foreground">WELCOME BACK</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight">Sign in to Kairos</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">Use the email address linked to your academic account.</p>
      </div>

      <form className="space-y-5" onSubmit={handleSubmit} noValidate>
        <div className="space-y-2">
          <Label htmlFor="email">Email address</Label>
          <div className="relative">
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
              className="h-11 pl-9"
            />
          </div>
          <p id="email-hint" className="text-xs text-muted-foreground">Enter the email address you used to register.</p>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <Label htmlFor="password">Password</Label>
            <Link to="/auth/auth2/forgot-password" className="text-sm font-medium underline underline-offset-4 hover:text-muted-foreground">Forgot password?</Link>
          </div>
          <div className="relative">
            <LockKeyhole aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              placeholder="Enter your password"
              required
              className="h-11 pl-9 pr-11"
            />
            <button
              type="button"
              onClick={() => setShowPassword((value) => !value)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
              className="absolute right-2 top-1/2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground outline-none hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
            >
              {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
            </button>
          </div>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Button type="submit" size="lg" className="h-11 w-full" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Sign in"}
          {!isSubmitting && <ArrowRight className="ml-2 size-4" />}
        </Button>
        <p className="text-center text-xs leading-5 text-muted-foreground">Your account access follows your institution’s permissions and verification requirements.</p>
      </form>
    </AuthFrame>
  );
};

export default BoxedLogin;
