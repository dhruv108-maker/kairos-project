import { Link } from "react-router";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  GraduationCap,
  ShieldCheck,
  Sparkles,
  UsersRound,
} from "lucide-react";
import FullLogo from "src/layouts/full/shared/logo/FullLogo";

const steps = [
  { number: "01", title: "Choose your role", description: "Tell Kairos how you belong to your academic community." },
  { number: "02", title: "Connect your institution", description: "Use the cohort or department details provided by your institution." },
  { number: "03", title: "Verify your email", description: "Confirm your email address before signing in." },
];

const Onboarding = () => (
  <main className="relative min-h-screen overflow-hidden bg-[#f6f8fc] text-slate-900">
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute -left-40 -top-40 h-[28rem] w-[28rem] rounded-full bg-indigo-200/40 blur-3xl" />
      <div className="absolute -bottom-48 -right-28 h-[34rem] w-[34rem] rounded-full bg-cyan-100/70 blur-3xl" />
      <div className="absolute inset-0 opacity-[0.22]" style={{ backgroundImage: "radial-gradient(#a5b4fc 0.8px, transparent 0.8px)", backgroundSize: "22px 22px" }} />
    </div>

    <header className="relative z-10 mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-10">
      <Link to="/onboarding" aria-label="Kairos home" className="inline-flex items-center rounded-xl bg-white px-3 py-2 shadow-sm ring-1 ring-slate-200/80"><FullLogo /></Link>
      <div className="hidden items-center gap-2 text-sm text-slate-500 sm:flex"><ShieldCheck className="h-4 w-4 text-indigo-600" />Secure academic identity</div>
      <p className="text-sm text-slate-600">Already registered? <Link to="/auth/auth2/login" className="font-semibold text-indigo-700 hover:underline">Sign in</Link></p>
    </header>

    <div className="relative z-10 mx-auto grid w-full max-w-7xl items-center gap-12 px-5 pb-14 pt-7 sm:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:gap-20 lg:px-10 lg:pb-20 lg:pt-12">
      <section className="max-w-2xl">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white/80 px-3.5 py-2 text-xs font-semibold tracking-wide text-indigo-700 shadow-sm"><Sparkles className="h-4 w-4" />WELCOME TO KAIROS</div>
        <h1 className="max-w-2xl text-4xl font-semibold leading-[1.1] tracking-[-0.045em] text-slate-950 sm:text-5xl xl:text-[3.8rem]">Your academic journey, <span className="text-indigo-600">all in one place.</span></h1>
        <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">A connected workspace for learning, teaching, and campus life. Let’s get your account set up with the right access for your role.</p>

        <div className="mt-9 grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-white bg-white/80 p-5 shadow-sm backdrop-blur">
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700"><BookOpen className="h-5 w-5" /></div>
            <h2 className="font-semibold text-slate-900">One connected workspace</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Bring your academic activities and community into a single home.</p>
          </div>
          <div className="rounded-2xl border border-white bg-white/80 p-5 shadow-sm backdrop-blur">
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700"><ShieldCheck className="h-5 w-5" /></div>
            <h2 className="font-semibold text-slate-900">Access with care</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Email verification and institutional approval help keep accounts appropriate.</p>
          </div>
        </div>

        <div className="mt-9 space-y-4">
          {steps.map((step) => (
            <div key={step.number} className="flex items-start gap-4">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-indigo-100 bg-white text-xs font-bold text-indigo-700">{step.number}</span>
              <div><h3 className="text-sm font-semibold text-slate-900">{step.title}</h3><p className="mt-1 text-sm leading-6 text-slate-500">{step.description}</p></div>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto w-full max-w-xl">
        <div className="overflow-hidden rounded-[1.75rem] border border-white/90 bg-white/95 shadow-[0_28px_90px_-38px_rgba(31,41,85,0.28)] ring-1 ring-slate-200/70 backdrop-blur">
          <div className="border-b border-slate-100 px-6 pb-6 pt-8 sm:px-8">
            <p className="text-sm font-semibold text-indigo-700">LET’S GET STARTED</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-[-0.035em] text-slate-950">How will you use Kairos?</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">Choose the option that matches your role. You’ll add your institution details next.</p>
          </div>
          <div className="space-y-4 px-6 py-6 sm:px-8 sm:py-8">
            <Link to="/auth/auth2/register?role=student" className="group flex items-start gap-4 rounded-2xl border border-slate-200 p-5 transition hover:border-indigo-300 hover:bg-indigo-50/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700"><GraduationCap className="h-6 w-6" /></span>
              <span className="min-w-0 flex-1"><span className="flex items-center justify-between gap-3 font-semibold text-slate-900">I’m a student <ArrowRight className="h-4 w-4 shrink-0 text-indigo-600 transition-transform group-hover:translate-x-1" /></span><span className="mt-1 block text-sm leading-6 text-slate-500">Join your cohort and access your student workspace.</span><span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-indigo-700"><CheckCircle2 className="h-3.5 w-3.5" />Student ID and cohort details required</span></span>
            </Link>
            <Link to="/auth/auth2/register?role=faculty" className="group flex items-start gap-4 rounded-2xl border border-slate-200 p-5 transition hover:border-cyan-300 hover:bg-cyan-50/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-600">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-cyan-50 text-cyan-800"><UsersRound className="h-6 w-6" /></span>
              <span className="min-w-0 flex-1"><span className="flex items-center justify-between gap-3 font-semibold text-slate-900">I’m faculty <ArrowRight className="h-4 w-4 shrink-0 text-cyan-700 transition-transform group-hover:translate-x-1" /></span><span className="mt-1 block text-sm leading-6 text-slate-500">Set up your teaching profile and department affiliation.</span><span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-cyan-800"><ShieldCheck className="h-3.5 w-3.5" />Institutional approval required</span></span>
            </Link>
            <div className="rounded-xl bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-500">Institute administrators manage institutional setup and access. If you don’t have your cohort or department details, contact your institution before registering.</div>
          </div>
          <div className="border-t border-slate-100 bg-slate-50/80 px-6 py-5 text-center text-sm text-slate-600 sm:px-8">Already have an account? <Link to="/auth/auth2/login" className="font-semibold text-indigo-700 hover:underline">Sign in <span aria-hidden="true">→</span></Link></div>
        </div>
      </section>
    </div>
  </main>
);

export default Onboarding;
