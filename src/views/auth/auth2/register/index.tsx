import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { ArrowRight, CheckCircle2, Eye, EyeOff, GraduationCap, LockKeyhole, Mail, UsersRound } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import AuthFrame from "@/components/auth/AuthFrame";
import { apiRequest } from "@/api/kairos-client";

type RegistrationRole = "student" | "faculty";

interface RegistrationResponse {
  account_id: string;
  message: string;
  verification_email_sent: boolean;
  activation_pending: boolean;
}

const BoxedRegister = () => {
  const [searchParams] = useSearchParams();
  const [role, setRole] = useState<RegistrationRole>(searchParams.get("role") === "faculty" ? "faculty" : "student");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [verificationSent, setVerificationSent] = useState(false);
  const [activationPending, setActivationPending] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  const handleRoleChange = (nextRole: RegistrationRole) => {
    setRole(nextRole);
    setError("");
    setMessage("");
    setVerificationSent(false);
    setActivationPending(false);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setMessage("");

    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const email = String(form.get("email") ?? "").trim().toLowerCase();
    const password = String(form.get("password") ?? "");
    const confirmPassword = String(form.get("confirm_password") ?? "");
    const fullName = String(form.get("full_name") ?? "").trim();

    if (password.length < 12 || password.length > 128) {
      setError("Choose a password between 12 and 128 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("The passwords do not match. Please check and try again.");
      return;
    }
    if (!acceptedTerms) {
      setError("Please confirm that you agree to the applicable terms and privacy policy.");
      return;
    }
    if (!fullName || !email) {
      setError("Enter your name and a valid email address to continue.");
      return;
    }

    const common = { email, password, full_name: fullName };
    const payload = role === "student"
      ? {
          ...common,
          enrollment_number: String(form.get("enrollment_number") ?? "").trim(),
          cohort_id: String(form.get("cohort_id") ?? "").trim(),
        }
      : {
          ...common,
          employee_code: String(form.get("employee_code") ?? "").trim(),
          department_id: String(form.get("department_id") ?? "").trim(),
          designation: String(form.get("designation") ?? "").trim(),
        };

    setIsSubmitting(true);
    try {
      const result = await apiRequest<RegistrationResponse>(`/auth/register/${role}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setRegisteredEmail(email);
      setMessage(result.message);
      setVerificationSent(result.verification_email_sent);
      setActivationPending(result.activation_pending);
      formElement.reset();
      setAcceptedTerms(false);
      setShowPassword(false);
      setShowConfirmPassword(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please review your details and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const resendVerification = async () => {
    if (!registeredEmail || isResending) return;
    setError("");
    setIsResending(true);
    try {
      const result = await apiRequest<{ message: string }>("/auth/verification/resend", {
        method: "POST",
        body: JSON.stringify({ email: registeredEmail }),
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
      asideEyebrow="Join your academic community"
      asideTitle="The right tools for your role. One connected academic space."
      asideDescription="Create your Kairos identity with the student or faculty details your institution uses to connect your account."
      footer={<>Already have an account? <Link to="/auth/auth2/login" className="font-medium text-foreground underline underline-offset-4 hover:text-muted-foreground">Sign in</Link></>}
    >
      {message ? (
        <div className="space-y-5">
          <div className="flex size-12 items-center justify-center rounded-full border border-border bg-muted">
            <CheckCircle2 className="size-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-muted-foreground">REGISTRATION RECEIVED</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Check your inbox</h1>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{message}</p>
          </div>
          <Alert>
            <Mail className="size-4" />
            <AlertTitle>{verificationSent ? "Verification email sent" : "Email verification may still be needed"}</AlertTitle>
            <AlertDescription>
              We’ll send instructions to <span className="font-medium text-foreground">{registeredEmail}</span> when delivery is available. Check your spam folder too.
              {activationPending ? " Faculty access also requires institutional approval." : ""}
            </AlertDescription>
          </Alert>
          <Button type="button" variant="outline" className="w-full" onClick={resendVerification} disabled={isResending}>
            {isResending ? "Requesting email…" : "Resend verification email"}
          </Button>
          <Button asChild className="w-full">
            <Link to="/auth/auth2/login">Continue to sign in <ArrowRight className="ml-2 size-4" /></Link>
          </Button>
          <button type="button" onClick={() => { setMessage(""); setVerificationSent(false); setActivationPending(false); }} className="w-full text-center text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground">
            Register another account
          </button>
          {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        </div>
      ) : (
        <>
          <div className="mb-7">
            <p className="text-sm font-medium text-muted-foreground">CREATE AN ACCOUNT</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Get started with Kairos</h1>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">Use the academic details provided by your institution.</p>
          </div>

          <div className="mb-6 grid grid-cols-2 gap-2" role="group" aria-label="Choose account type">
            <Button type="button" variant={role === "student" ? "default" : "outline"} className="h-10" aria-pressed={role === "student"} onClick={() => handleRoleChange("student")}>
              <GraduationCap className="mr-2 size-4" /> Student
            </Button>
            <Button type="button" variant={role === "faculty" ? "default" : "outline"} className="h-10" aria-pressed={role === "faculty"} onClick={() => handleRoleChange("faculty")}>
              <UsersRound className="mr-2 size-4" /> Faculty
            </Button>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="full_name">Full name</Label>
              <Input id="full_name" name="full_name" autoComplete="name" placeholder="Your full name" maxLength={255} required className="h-11" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email address</Label>
              <div className="relative">
                <Mail aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input id="email" name="email" type="email" autoComplete="email" autoCapitalize="none" spellCheck={false} placeholder="you@institution.edu" maxLength={255} required className="h-11 pl-9" />
              </div>
            </div>

            {role === "student" ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="enrollment_number">Enrollment number</Label>
                  <Input id="enrollment_number" name="enrollment_number" autoComplete="off" placeholder="Student ID" maxLength={64} required className="h-11" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="cohort_id">Cohort ID</Label>
                  <Input id="cohort_id" name="cohort_id" autoComplete="off" placeholder="Provided by your institution" maxLength={36} required className="h-11" />
                </div>
              </div>
            ) : (
              <>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="employee_code">Employee code</Label>
                    <Input id="employee_code" name="employee_code" autoComplete="off" placeholder="Staff ID" maxLength={64} required className="h-11" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="designation">Designation</Label>
                    <Input id="designation" name="designation" placeholder="e.g. Assistant Professor" maxLength={100} required className="h-11" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="department_id">Department ID</Label>
                  <Input id="department_id" name="department_id" autoComplete="off" placeholder="Provided by your institution" maxLength={36} required className="h-11" />
                </div>
              </>
            )}

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <LockKeyhole aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={12} maxLength={128} placeholder="At least 12 characters" required className="h-11 pl-9 pr-11" />
                <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} className="absolute right-2 top-1/2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground">Use 12–128 characters.</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm_password">Confirm password</Label>
              <div className="relative">
                <Input id="confirm_password" name="confirm_password" type={showConfirmPassword ? "text" : "password"} autoComplete="new-password" minLength={12} maxLength={128} placeholder="Enter your password again" required className="h-11 pr-11" />
                <button type="button" onClick={() => setShowConfirmPassword((value) => !value)} aria-label={showConfirmPassword ? "Hide confirmation password" : "Show confirmation password"} aria-pressed={showConfirmPassword} className="absolute right-2 top-1/2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  {showConfirmPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-start gap-2.5 pt-1">
              <Checkbox id="terms" checked={acceptedTerms} onCheckedChange={(checked) => setAcceptedTerms(checked === true)} className="mt-0.5" />
              <Label htmlFor="terms" className="cursor-pointer text-sm font-normal leading-5 text-muted-foreground">
                I agree to the applicable terms and privacy policy.
              </Label>
            </div>

            {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

            <Button type="submit" size="lg" className="h-11 w-full" disabled={isSubmitting}>
              {isSubmitting ? "Creating your account…" : "Create account"}
              {!isSubmitting && <ArrowRight className="ml-2 size-4" />}
            </Button>
            <p className="text-center text-xs leading-5 text-muted-foreground">
              By creating an account, you’ll receive an email verification link. Faculty accounts also require institutional approval.
            </p>
          </form>
        </>
      )}
    </AuthFrame>
  );
};

export default BoxedRegister;
