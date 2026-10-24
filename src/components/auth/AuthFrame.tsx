import type { ReactNode } from "react";
import { Link } from "react-router";
import { ArrowUpRight, ShieldCheck } from "lucide-react";
import FullLogo from "src/layouts/full/shared/logo/FullLogo";

interface AuthFrameProps {
  children: ReactNode;
  asideEyebrow: string;
  asideTitle: string;
  asideDescription: string;
  brandHref?: string;
  footer?: ReactNode;
}

export default function AuthFrame({
  children,
  asideEyebrow,
  asideTitle,
  asideDescription,
  brandHref = "/onboarding",
  footer,
}: AuthFrameProps) {
  return (
    <main className="min-h-svh bg-background text-foreground lg:grid lg:min-h-screen lg:grid-cols-[minmax(0,0.92fr)_minmax(480px,1.08fr)]">
      <aside className="relative hidden min-h-screen flex-col justify-between overflow-hidden bg-zinc-950 px-10 py-9 text-zinc-50 lg:flex xl:px-14 xl:py-11">
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 opacity-[0.08]">
          <div className="absolute inset-x-0 top-1/4 border-t border-white" />
          <div className="absolute inset-x-0 top-2/4 border-t border-white" />
          <div className="absolute inset-x-0 top-3/4 border-t border-white" />
          <div className="absolute inset-y-0 left-1/4 border-l border-white" />
          <div className="absolute inset-y-0 left-2/4 border-l border-white" />
          <div className="absolute inset-y-0 left-3/4 border-l border-white" />
        </div>
        <Link to={brandHref} aria-label="Kairos home" className="relative z-10 inline-flex w-fit items-center rounded-md bg-white px-3 py-2.5">
          <FullLogo />
        </Link>
        <div className="relative z-10 max-w-xl py-16">
          <p className="mb-5 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.2em] text-zinc-400">
            <span className="h-px w-7 bg-zinc-500" />
            {asideEyebrow}
          </p>
          <h1 className="max-w-lg text-4xl font-medium leading-[1.12] tracking-[-0.045em] text-white xl:text-5xl">
            {asideTitle}
          </h1>
          <p className="mt-6 max-w-md text-base leading-7 text-zinc-400">{asideDescription}</p>
          <div className="mt-10 flex items-center gap-3 border-t border-white/15 pt-5 text-sm text-zinc-300">
            <ShieldCheck className="size-4 text-zinc-400" />
            Identity and access designed for academic communities
          </div>
        </div>
        <div className="relative z-10 flex items-center justify-between gap-4 text-xs text-zinc-500">
          <span>© {new Date().getFullYear()} Kairos</span>
          <span className="inline-flex items-center gap-1.5">One academic workspace <ArrowUpRight className="size-3.5" /></span>
        </div>
      </aside>

      <section className="flex min-h-svh flex-col px-5 py-6 sm:px-8 sm:py-8 lg:min-h-screen lg:px-12 xl:px-16">
        <header className="flex items-center justify-between gap-4 lg:hidden">
          <Link to={brandHref} aria-label="Kairos home" className="inline-flex items-center rounded-md border border-border bg-background px-2.5 py-2">
            <FullLogo />
          </Link>
          <span className="text-xs text-muted-foreground">Secure academic access</span>
        </header>
        <div className="flex flex-1 items-center justify-center py-8 lg:py-12">
          <div className="w-full max-w-md">{children}</div>
        </div>
        {footer ? <footer className="mx-auto w-full max-w-md pb-2 text-center text-sm text-muted-foreground">{footer}</footer> : null}
      </section>
    </main>
  );
}
