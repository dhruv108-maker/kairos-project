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
    <main className="min-h-svh w-full min-w-0 overflow-x-clip bg-background text-foreground lg:grid lg:min-h-screen lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
      <aside className="relative hidden min-h-screen min-w-0 flex-col justify-between overflow-hidden bg-zinc-950 px-10 py-9 text-zinc-50 lg:flex xl:px-14 xl:py-11">
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 opacity-[0.08]">
          <div className="absolute inset-x-0 top-1/4 border-t border-white" />
          <div className="absolute inset-x-0 top-2/4 border-t border-white" />
          <div className="absolute inset-x-0 top-3/4 border-t border-white" />
          <div className="absolute inset-y-0 left-1/4 border-l border-white" />
          <div className="absolute inset-y-0 left-2/4 border-l border-white" />
          <div className="absolute inset-y-0 left-3/4 border-l border-white" />
        </div>
        <Link to={brandHref} aria-label="Kairos home" className="relative z-10 inline-flex w-fit max-w-full items-center rounded-md bg-white px-3 py-2.5">
          <FullLogo />
        </Link>
        <div className="relative z-10 min-w-0 max-w-xl py-16">
          <p className="mb-5 flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-[0.2em] text-zinc-400">
            <span className="h-px w-7 shrink-0 bg-zinc-500" />
            {asideEyebrow}
          </p>
          <h1 className="max-w-lg break-words text-4xl font-medium leading-[1.12] tracking-[-0.045em] text-white xl:text-5xl">
            {asideTitle}
          </h1>
          <p className="mt-6 max-w-md break-words text-base leading-7 text-zinc-400">{asideDescription}</p>
          <div className="mt-10 flex min-w-0 items-center gap-3 border-t border-white/15 pt-5 text-sm text-zinc-300">
            <ShieldCheck className="size-4 shrink-0 text-zinc-400" />
            <span>Identity and access designed for academic communities</span>
          </div>
        </div>
        <div className="relative z-10 flex items-center justify-between gap-4 text-xs text-zinc-500">
          <span>© {new Date().getFullYear()} Kairos</span>
          <span className="inline-flex items-center gap-1.5 text-right">One academic workspace <ArrowUpRight className="size-3.5 shrink-0" /></span>
        </div>
      </aside>

      <section className="flex min-h-svh min-w-0 flex-col px-4 py-5 sm:px-8 sm:py-8 lg:min-h-screen lg:px-10 xl:px-16">
        <header className="flex min-w-0 items-center justify-between gap-3 lg:hidden">
          <Link to={brandHref} aria-label="Kairos home" className="inline-flex min-w-0 max-w-[65%] items-center rounded-md border border-border bg-background px-2.5 py-2">
            <FullLogo />
          </Link>
          <span className="text-right text-xs text-muted-foreground">Secure academic access</span>
        </header>
        <div className="flex min-w-0 flex-1 items-center justify-center py-7 sm:py-8 lg:py-12">
          <div className="w-full min-w-0 max-w-md">{children}</div>
        </div>
        {footer ? <footer className="mx-auto w-full min-w-0 max-w-md break-words pb-2 text-center text-sm text-muted-foreground">{footer}</footer> : null}
      </section>
    </main>
  );
}
