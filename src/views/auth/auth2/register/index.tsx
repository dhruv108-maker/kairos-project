import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import {
  ArrowRight,
  BookOpen,
  Building2,
  CheckCircle2,
  Eye,
  EyeOff,
  GraduationCap,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Sparkles,
  UsersRound,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import FullLogo from "src/layouts/full/shared/logo/FullLogo";
import { apiRequest } from "@/api/kairos-client";

type RegistrationRole = "student" | "faculty";

interface RegistrationResponse {
  account_id: string;
  message: string;
  verification_email_sent: boolean;
  activation_pending: boolean;
}

const BoxedRegister = () => {
  const [searchParams, setSearchParams] = useSearchParams();\n  const [role, setRole] = useState<RegistrationRole>(searchParams.get("role") === "faculty" ? "faculty" : "student");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [verificationSent, setVerificationSent] = useState<boolean | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleRoleChange = (nextRole: RegistrationRole) => {
    setRole(nextRole);
    setError("");
    setMessage("");
    setVerificationSent(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    setError("");
    setMessage("");
    setVerificationSent(null);

    const form = new FormData(formElement);
    const password = String(form.get("password") ?? "");
    const confirmPassword = String(form.get("confirm_password") ?? "");
    if (password.length < 12) {
      setError("Your password must contain at least 12 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("The passwords do not match. Please check and try again.");
      return;
    }
    if (!form.get("terms")) {
      setError("Please confirm that you agree to the terms and privacy policy.");
      return;
    }

    setIsSubmitting(true);
    const common = {
      email: String(form.get("email") ?? "").trim().toLowerCase(),
      password,
      full_name: String(form.get("full_name") ?? "").trim(),
    };
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

    try {
      const result = await apiRequest<RegistrationResponse>(`/auth/register/${role}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setMessage(result.message);
      setVerificationSent(result.verification_email_sent);
      formElement.reset();
      setShowPassword(false);
      setShowConfirmPassword(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please check your details and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="kairos-signup relative min-h-screen overflow-hidden bg-[#f6f8fc] text-slate-900">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-40 -top-40 h-[28rem] w-[28rem] rounded-full bg-indigo-200/35 blur-3xl" />
        <div className="absolute -bottom-48 -right-28 h-[34rem] w-[34rem] rounded-full bg-cyan-100/60 blur-3xl" />
        <div className="absolute inset-0 opacity-[0.24]" style={{ backgroundImage: "radial-gradient(#a5b4fc 0.8px, transparent 0.8px)", backgroundSize: "22px 22px" }} />
      </div>

      <header className="relative z-10 mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-10">
        <Link to="/auth/auth2/login" aria-label="Kairos home" className="inline-flex items-center rounded-xl bg-white px-3 py-2 shadow-sm ring-1 ring-slate-200/80">
          <FullLogo />
        </Link>
        <div className="hidden items-center gap-2 text-sm text-slate-500 sm:flex">
          <ShieldCheck className="h-4 w-4 text-indigo-600" />
          Secure academic identity
        </div>
        <p className="text-sm text-slate-600 sm:hidden">
          <Link to="/auth/auth2/login" className="font-semibold text-indigo-700">Sign in</Link>
        </p>
      </header>

      <div className="relative z-10 mx-auto grid w-full max-w-7xl items-center gap-10 px-5 pb-12 pt-4 sm:px-8 lg:grid-cols-[0.92fr_1.08fr] lg:gap-16 lg:px-10 lg:pb-20 lg:pt-8">
        <section className="hidden max-w-xl lg:block">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white/80 px-3.5 py-2 text-xs font-semibold tracking-wide text-indigo-700 shadow-sm">
            <Sparkles className="h-4 w-4" />
            ONE CONNECTED ACADEMIC WORKSPACE
          </div>
          <h1 className="max-w-lg text-5xl font-semibold leading-[1.12] tracking-[-0.045em] text-slate-950 xl:text-[3.65rem]">
            Your next chapter starts <span className="text-indigo-600">here.</span>
          </h1>
          <p className="mt-5 max-w-md text-lg leading-8 text-slate-600">
            Bring learning, teaching, and campus life together in one secure space built around your institution.
          </p>

          <div className="mt-10 space-y-4">
            <div className="flex items-start gap-4 rounded-2xl border border-white/90 bg-white/75 p-4 shadow-sm backdrop-blur">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700">
                <GraduationCap className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-semibold text-slate-900">A workspace that fits your role</h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">Student and faculty access with role-aware academic tools.</p>
              </div>
            </div>
            <div className="flex items-start gap-4 rounded-2xl border border-white/90 bg-white/75 p-4 shadow-sm backdrop-blur">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-cyan-50 text-cyan-800">
                <Building2 className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-semibold text-slate-900">Connected to your institution</h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">Your cohort or department helps connect your account to the right academic community.</p>
              </div>
            </div>
            <div className="flex items-start gap-4 rounded-2xl border border-white/90 bg-white/75 p-4 shadow-sm backdrop-blur">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                <LockKeyhole className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-semibold text-slate-900">Account security from day one</h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">Email verification and institution approval help protect academic access.</p>
              </div>
            </div>
          </div>

          <div className="mt-9 flex items-center gap-3 text-sm text-slate-500">
            <div className="flex -space-x-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-[#f6f8fc] bg-indigo-100 text-indigo-700"><BookOpen className="h-4 w-4" /></span>
              <span className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-[#f6f8fc] bg-cyan-100 text-cyan-800"><UsersRound className="h-4 w-4" /></span>
              <span className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-[#f6f8fc] bg-emerald-100 text-emerald-800"><ShieldCheck className="h-4 w-4" /></span>
            </div>
            <span>One identity. The right access. A clearer academic journey.</span>
          </div>
        </section>

        <section className="mx-auto w-full max-w-2xl">
          <Card className="overflow-hidden rounded-[1.75rem] border border-white/90 bg-white/95 p-0 shadow-[0_28px_90px_-38px_rgba(31,41,85,0.28)] ring-1 ring-slate-200/70 backdrop-blur">
            <div className="border-b border-slate-100 px-6 pb-6 pt-7 sm:px-9 sm:pt-9">
              <div className="mb-5 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-indigo-700 lg:hidden">
                <Sparkles className="h-4 w-4" />
                Welcome to Kairos
              </div>
              <p className="text-sm font-semibold text-indigo-700">CREATE YOUR ACCOUNT</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-[-0.035em] text-slate-950">Join your academic community</h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                Enter the details associated with your institution. Fields marked required must be completed.
              </p>

              <div className="mt-6 grid grid-cols-2 gap-3 rounded-2xl bg-slate-50 p-1.5">
                <button
                  type="button"
                  onClick={() => handleRoleChange("student")}
                  aria-pressed={role === "student"}
                  className={`flex min-h-12 items-center justify-center gap-2 rounded-xl px-3 py-3 text-sm font-semibold transition-all ${role === "student" ? "bg-white text-indigo-700 shadow-sm ring-1 ring-slate-200/80" : "text-slate-500 hover:text-slate-800"}`}
                >
                  <GraduationCap className="h-4 w-4" />
                  Student
                </button>
                <button
                  type="button"
                  onClick={() => handleRoleChange("faculty")}
                  aria-pressed={role === "faculty"}
                  className={`flex min-h-12 items-center justify-center gap-2 rounded-xl px-3 py-3 text-sm font-semibold transition-all ${role === "faculty" ? "bg-white text-indigo-700 shadow-sm ring-1 ring-slate-200/80" : "text-slate-500 hover:text-slate-800"}`}
                >
                  <UsersRound className="h-4 w-4" />
                  Faculty
                </button>
              </div>
            </div>

            <form className="space-y-5 px-6 py-6 sm:px-9 sm:py-8" onSubmit={handleSubmit}>
              <div className="grid gap-5 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="full_name" className="text-sm font-medium text-slate-700">Full name <span className="text-rose-500">*</span></Label>
                  <Input id="full_name" name="full_name" autoComplete="name" placeholder="e.g. Aanya Sharma" maxLength={255} required className="h-12 rounded-xl border-slate-200 bg-white px-3.5 placeholder:text-slate-400 focus-visible:border-indigo-500 focus-visible:ring-indigo-500/15" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-sm font-medium text-slate-700">Institutional email <span className="text-rose-500">*</span></Label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input id="email" name="email" type="email" autoComplete="email" placeholder="you@college.edu" maxLength={255} required className="h-12 rounded-xl border-slate-200 bg-white pl-10 pr-3.5 placeholder:text-slate-400 focus-visible:border-indigo-500 focus-visible:ring-indigo-500/15" />
                  </div>
                </div>
              </div>

              {role === "student" ? (
                <div className="grid gap-5 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="enrollment_number" className="text-sm font-medium text-slate-700">Enrollment number <span className="text-rose-500">*</span></Label>
                    <Input id="enrollment_number" name="enrollment_number" autoComplete="off" placeholder="Your student ID" maxLength={64} required key="student-enrollment" className="h-12 rounded-xl border-slate-200 bg-white placeholder:text-slate-400 focus-visible:border-indigo-500 focus-visible:ring-indigo-500/15" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="cohort_id" className="text-sm font-medium text-slate-700">Cohort ID <span className="text-rose-500">*</span></Label>
                    <Input id="cohort_id" name="cohort_id" autoComplete="off" placeholder="Provided by your institution" maxLength={36} required key="student-cohort" className="h-12 rounded-xl border-slate-200 bg-white placeholder:text-slate-400 focus-visible:border-indigo-500 focus-visible:ring-indigo-500/15" />
                    <p className="text-xs leading-5 text-slate-500">Ask your institution if you do not know your cohort ID.</p>
                  </div>
                </div>
              ) : (
                <>
                  <div className="grid gap-5 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="employee_code" className="text-sm font-medium text-slate-700">Employee code <span className="text-rose-500">*</span></Label>
                      <Input id="employee_code" name="employee_code" autoComplete="off" placeholder="Your staff ID" maxLength={64} required key="faculty-employee" className="h-12 rounded-xl border-slate-200 bg-white placeholder:text-slate-400 focus-visible:border-indigo-500 focus-visible:ring-indigo-500/15" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="designation" className="text-sm font-medium text-slate-700">Designation <span className="text-rose-500">*</span></Label>
                      <Input id="designation" name="designation" placeholder="e.g. Assistant Professor" maxLength={100} required key="faculty-designation" className="h-12 rounded-xl border-slate-200 bg-white placeholder:text-slate-400 focus-visible:border-indigo-500 focus-visible:ring-indigo-500/15" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="department_id" className="text-sm font-medium text-slate-700">Department ID <span className="text-rose-500">*</span></Label>
                    <Input id="department_id" name="department_id" autoComplete="off" placeholder="Provided by your institution" maxLength={36} required key="faculty-department" className="h-12 rounded-xl border-slate-200 bg-white placeholder:text-slate-400 focus-visible:border-indigo-500 focus-visible:ring-indigo-500/15" />
                    <p className="text-xs leading-5 text-slate-500">Faculty access remains pending until institutional approval.</p>
                  </div>
                </>
              )}

              <div className="grid gap-5 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="password" className="text-sm font-medium text-slate-700">Create password <span className="text-rose-500">*</span></Label>
                  <div className="relative">
                    <LockKeyhole className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={12} maxLength={128} required placeholder="At least 12 characters" className="h-12 rounded-xl border-slate-200 bg-white pl-10 pr-11 placeholder:text-slate-400 focus-visible:border-indigo-500 focus-visible:ring-indigo-500/15" />
                    <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 hover:text-slate-700">
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  <p className="text-xs text-slate-500">Use 12 or more characters.</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm_password" className="text-sm font-medium text-slate-700">Confirm password <span className="text-rose-500">*</span></Label>
                  <div className="relative">
                    <LockKeyhole className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input id="confirm_password" name="confirm_password" type={showConfirmPassword ? "text" : "password"} autoComplete="new-password" minLength={12} maxLength={128} required placeholder="Re-enter password" className="h-12 rounded-xl border-slate-200 bg-white pl-10 pr-11 placeholder:text-slate-400 focus-visible:border-indigo-500 focus-visible:ring-indigo-500/15" />
                    <button type="button" onClick={() => setShowConfirmPassword((value) => !value)} aria-label={showConfirmPassword ? "Hide confirmation password" : "Show confirmation password"} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 hover:text-slate-700">
                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              </div>

              <label className="flex cursor-pointer items-start gap-3 text-sm leading-6 text-slate-600">
                <input name="terms" type="checkbox" required className="mt-1 h-4 w-4 shrink-0 rounded border-slate-300 accent-indigo-600 focus:ring-indigo-500" />
                <span>I agree to the <a href="/terms" className="font-semibold text-indigo-700 underline-offset-4 hover:underline">Terms of Service</a> and <a href="/privacy" className="font-semibold text-indigo-700 underline-offset-4 hover:underline">Privacy Policy</a>.</span>
              </label>

              {message && (
                <div role="status" aria-live="polite" className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm leading-6 text-emerald-900">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
                  <div>
                    <p className="font-semibold">{verificationSent ? "Your registration has been received" : "Account created"}</p>
                    <p className="mt-1">{message}</p>
                    {verificationSent === false && <p className="mt-2 font-medium">Email delivery is currently unavailable. Contact your institution administrator if you need help verifying your account.</p>}
                  </div>
                </div>
              )}
              {error && (
                <div role="alert" aria-live="assertive" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-800">
                  {error}
                </div>
              )}

              <Button type="submit" size="lg" className="group h-12 w-full rounded-xl bg-indigo-600 text-sm font-semibold text-white shadow-[0_10px_20px_-10px_rgba(79,70,229,0.75)] transition hover:bg-indigo-700" disabled={isSubmitting}>
                {isSubmitting ? "Creating your account…" : "Create account"}
                {!isSubmitting && <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-0.5" />}
              </Button>
              <p className="text-center text-xs leading-5 text-slate-500">
                By continuing, you confirm that the details provided are accurate and belong to you.
              </p>
            </form>

            <div className="border-t border-slate-100 bg-slate-50/80 px-6 py-5 text-center text-sm text-slate-600 sm:px-9">
              Already have a Kairos account?{" "}
              <Link className="font-semibold text-indigo-700 hover:text-indigo-800 hover:underline" to="/auth/auth2/login">Sign in <span aria-hidden="true">→</span></Link>
            </div>
          </Card>
          <p className="mt-5 text-center text-xs text-slate-500">
            <ShieldCheck className="mr-1 inline h-3.5 w-3.5 align-[-2px]" />
            Your information is handled securely and used to set up your academic account.
          </p>
        </section>
      </div>
    </main>
  );
};

export default BoxedRegister;
