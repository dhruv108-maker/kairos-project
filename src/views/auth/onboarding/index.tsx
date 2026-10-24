import { Link } from "react-router";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  GraduationCap,
  Landmark,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import FullLogo from "src/layouts/full/shared/logo/FullLogo";

const steps = [
  {
    number: "01",
    title: "Choose your role",
    description: "Start as a student or faculty member. Your role determines the academic details requested.",
  },
  {
    number: "02",
    title: "Connect your institution",
    description: "Keep your cohort ID or department ID and student or employee number handy.",
  },
  {
    number: "03",
    title: "Verify and get access",
    description: "Confirm your email. Faculty accounts also require institutional approval before access is activated.",
  },
];

const Onboarding = () => (
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
      <p className="text-sm text-slate-600">Already have an account? <Link to="/auth/auth2/login" className="font-semibold text-indigo-700 hover:underline">Sign in</Link></p>
    </header>

    <div className="relative z-10 mx-auto grid w-full max-w-7xl items-center gap-12 px-5 pb-16 pt-6 sm:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:gap-20 lg:px-10 lg:pb-24 lg:pt-12">
      <section>
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white/80 px-3.5 py-2 text-xs font-semibold tracking-wide text-indigo-700 shadow-sm">
          <Landmark className="h-4 w-4" /> YOUR ACADEMIC COMMUNITY, CONNECTED
        </div>
        <h1 className="max-w-2xl text-4xl font-semibold leading-[1.12] tracking-[-0.045em] text-slate-950 sm:text-5xl xl:text-[3.8rem]">
          A better start to your <span className="text-indigo-600">Kairos journey.</span>
        </h1>
        <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
          One secure academic workspace for learning, teaching, and the people who make your institution thrive.
        </p>

        <div className="mt-9 grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-white bg-white/80 p-5 shadow-sm backdrop-blur">
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700"><GraduationCap className="h-5 w-5" /></div>
            <h2 className="font-semibold text-slate-900">For students</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Join your academic cohort and access tools tailored to your learning journey.</p>
            <Link to="/auth/auth2/register?role=student" className="mt-4 inline-flex items-center text-sm font-semibold text-indigo-700 hover:text-indigo-800">Continue as student <ArrowRight className="ml-2 h-4 w-4" /></Link>
          </div>
          <div className="rounded-2xl border border-white bg-white/80 p-5 shadow-sm backdrop-blur">
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-50 text-cyan-800"><UsersRound className="h-5 w-5" /></div>
            <h2 className="font-semibold text-slate-900">For faculty</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Connect your department and create an account for institutional review.</p>
            <Link to="/auth/auth2/register?role=faculty" className="mt-4 inline-flex items-center text-sm font-semibold text-indigo-700 hover:text-indigo-800">Continue as faculty <ArrowRight className="ml-2 h-4 w-4" /></Link>
          </div>
        </div>
        <p className="mt-6 flex items-center gap-2 text-sm text-slate-500"><ShieldCheck className="h-4 w-4 text-emerald-600" /> Email verification helps protect access to your account.</p>
      </section>

      <section className="rounded-[1.75rem] border border-white/90 bg-white/95 p-6 shadow-[0_28px_90px_-38px_rgba(31,41,85,0.28)] ring-1 ring-slate-200/70 backdrop-blur sm:p-9">
        <div className="mb-7 flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-700"><BookOpen className="h-5 w-5" /></div>
          <div>
            <p className="text-sm font-semibold text-indigo-700">GETTING STARTED</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">Your first three steps</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">A quick checklist before you create your account.</p>
          </div>
        </div>
        <ol className="space-y-6">
          {steps.map((step, index) => (
            <li key={step.number} className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-indigo-100 bg-indigo-50 text-sm font-semibold text-indigo-700">{step.number}</div>
              <div className={index < steps.length - 1 ? "flex-1 border-b border-slate-100 pb-6" : "flex-1"}>
                <h3 className="font-semibold text-slate-900">{step.title}</h3>
                <p className="mt-1 text-sm leading-6 text-slate-600">{step.description}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="mt-8 rounded-2xl border border-emerald-100 bg-emerald-50/70 p-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-emerald-900"><CheckCircle2 className="h-4 w-4" /> Have your institution details ready</p>
          <p className="mt-1 text-sm leading-6 text-emerald-800">If you do not know your cohort or department ID, ask your institution administrator before registering.</p>
        </div>
        <Link to="/auth/auth2/register" className="mt-6 inline-flex h-12 w-full items-center justify-center rounded-xl bg-indigo-600 px-4 text-sm font-semibold text-white transition hover:bg-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2">
          Create your account <ArrowRight className="ml-2 h-4 w-4" />
        </Link>
      </section>
    </div>
    <footer className="relative z-10 mx-auto max-w-7xl px-5 pb-8 text-center text-xs text-slate-500 sm:px-8 lg:px-10">
      Secure academic access, with verification and institution-aware permissions.
    </footer>
  </main>
);

export default Onboarding;
