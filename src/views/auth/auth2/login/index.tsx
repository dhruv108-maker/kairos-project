import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import {
  ArrowRight,
  BookOpen,
  Eye,
  EyeOff,
  GraduationCap,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import FullLogo from "src/layouts/full/shared/logo/FullLogo";
import { useAuth } from "@/context/auth/AuthContext";

const BoxedLogin = () => {
  const navigate = useNavigate();
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
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#f6f8fc] text-slate-900">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-40 -top-40 h-[28rem] w-[28rem] rounded-full bg-indigo-200/40 blur-3xl" />
        <div className="absolute -bottom-48 -right-28 h-[34rem] w-[34rem] rounded-full bg-cyan-100/70 blur-3xl" />
        <div className="absolute inset-0 opacity-[0.22]" style={{ backgroundImage: "radial-gradient(#a5b4fc 0.8px, transparent 0.8px)", backgroundSize: "22px 22px" }} />
      </div>

      <header className="relative z-10 mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-10">
        <Link to="/onboarding" aria-label="Kairos home" className="inline-flex items-center rounded-xl bg-white px-3 py-2 shadow-sm ring-1 ring-slate-200/80">
          <FullLogo />
        </Link>
        <div className="hidden items-center gap-2 text-sm text-slate-500 sm:flex">
          <ShieldCheck className="h-4 w-4 text-indigo-600" />
          Secure academic identity
        </div>
        <p className="text-sm text-slate-600 sm:hidden">New to Kairos? <Link to="/onboarding" className="font-semibold text-indigo-700">Get started</Link></p>
      </header>

      <div className="relative z-10 mx-auto grid w-full max-w-7xl items-center gap-12 px-5 pb-12 pt-5 sm:px-8 lg:grid-cols-[1fr_0.9fr] lg:gap-20 lg:px-10 lg:pb-20 lg:pt-10">
        <section className="hidden max-w-xl lg:block">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white/80 px-3.5 py-2 text-xs font-semibold tracking-wide text-indigo-700 shadow-sm">
            <Sparkles className="h-4 w-4" /> YOUR ACADEMIC WORKSPACE
          </div>
          <h1 className="max-w-xl text-5xl font-semibold leading-[1.1] tracking-[-0.045em] text-slate-950 xl:text-[3.8rem]">
            Good to have you <span className="text-indigo-600">back.</span>
          </h1>
          <p className="mt-5 max-w-lg text-lg leading-8 text-slate-600">
            Pick up where you left off. Your learning, teaching, and academic community come together in one secure place.
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-white bg-white/80 p-5 shadow-sm backdrop-blur">
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700"><GraduationCap className="h-5 w-5" /></div>
              <h2 className="font-semibold text-slate-900">Built around your role</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">Relevant academic tools for students and faculty.</p>
            </div>
            <div className="rounded-2xl border border-white bg-white/80 p-5 shadow-sm backdrop-blur">
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-50 text-cyan-800"><BookOpen className="h-5 w-5" /></div>
              <h2 className="font-semibold text-slate-900">One connected space</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">Stay connected to your institution and academic journey.</p>
            </div>
          </div>
          <p className="mt-8 flex items-center gap-2 text-sm text-slate-500"><ShieldCheck className="h-4 w-4 text-emerald-600" /> Your account and access are protected.</p>
        </section>

        <section className="mx-auto w-full max-w-md">
          <div className="mb-6 text-center lg:hidden">
            <div className="mb-4 flex justify-center"><Sparkles className="h-5 w-5 text-indigo-600" /></div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Welcome back</h1>
            <p className="mt-2 text-sm text-slate-500">Sign in to your Kairos academic workspace.</p>
          </div>
          <div className="overflow-hidden rounded-[1.75rem] border border-white/90 bg-white/95 shadow-[0_28px_90px_-38px_rgba(31,41,85,0.28)] ring-1 ring-slate-200/70 backdrop-blur">
            <div className="border-b border-slate-100 px-6 pb-6 pt-8 sm:px-8">
              <div className="hidden lg:block"><p className="text-sm font-semibold text-indigo-700">WELCOME BACK</p></div>
              <h2 className="mt-2 text-3xl font-semibold tracking-[-0.035em] text-slate-950">Sign in to Kairos</h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">Use the email address associated with your account.</p>
            </div>
            <form className="space-y-5 px-6 py-7 sm:px-8" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium text-slate-700">Email address</Label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input id="email" name="email" type="email" autoComplete="username" placeholder="you@institution.edu" maxLength={255} required className="h-12 rounded-xl border-slate-200 pl-10 placeholder:text-slate-400 focus-visible:border-indigo-500 focus-visible:ring-indigo-500/15" />
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <Label htmlFor="password" className="text-sm font-medium text-slate-700">Password</Label>
                  <Link to="/auth/auth2/forgot-password" className="text-sm font-semibold text-indigo-700 hover:text-indigo-800 hover:underline">Forgot password?</Link>
                </div>
                <div className="relative">
                  <LockKeyhole className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="Enter your password" required className="h-12 rounded-xl border-slate-200 pl-10 pr-11 placeholder:text-slate-400 focus-visible:border-indigo-500 focus-visible:ring-indigo-500/15" />
                  <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 hover:text-slate-700">
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
              {error && <div role="alert" aria-live="assertive" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-800">{error}</div>}
              <Button type="submit" size="lg" className="group h-12 w-full rounded-xl bg-indigo-600 text-sm font-semibold text-white shadow-[0_10px_20px_-10px_rgba(79,70,229,0.75)] transition hover:bg-indigo-700" disabled={isSubmitting}>
                {isSubmitting ? "Signing you in…" : "Sign in"}
                {!isSubmitting && <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-0.5" />}
              </Button>
              <p className="text-center text-xs leading-5 text-slate-500">By signing in, you agree to use Kairos in accordance with your institution's policies.</p>
            </form>
            <div className="border-t border-slate-100 bg-slate-50/80 px-6 py-5 text-center text-sm text-slate-600 sm:px-8">
              New to Kairos? <Link className="font-semibold text-indigo-700 hover:text-indigo-800 hover:underline" to="/onboarding">Create your account <span aria-hidden="true">→</span></Link>
            </div>
          </div>
          <p className="mt-5 text-center text-xs text-slate-500"><ShieldCheck className="mr-1 inline h-3.5 w-3.5 align-[-2px]" />Secure sign-in for your academic community.</p>
        </section>
      </div>
    </main>
  );
};

export default BoxedLogin;
