import type { ReactNode } from "react";
import { Link } from "react-router";
import FullLogo from "src/layouts/full/shared/logo/FullLogo";
import DotGrid from "@/components/ui/DotGrid";

interface AuthFrameProps {
  children: ReactNode;
  asideEyebrow: string;
  asideTitle: string;
  asideDescription: string;
  brandHref?: string;
  footer?: ReactNode;
  showDotGrid?: boolean;
}

export default function AuthFrame({
  children,
  asideTitle,
  brandHref = "/onboarding",
  footer,
  showDotGrid = false,
}: AuthFrameProps) {

  return (
    <main className="min-h-svh w-full min-w-0 overflow-x-clip bg-background text-foreground lg:grid lg:min-h-screen lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
      <aside className="relative flex min-h-[230px] min-w-0 flex-col justify-between overflow-hidden bg-white px-5 py-5 text-zinc-950 sm:min-h-[260px] sm:px-8 sm:py-7 lg:min-h-screen lg:px-10 lg:py-9 xl:px-14 xl:py-11">
        {showDotGrid ? <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-[3]"><DotGrid className="h-full w-full" baseColor="#3a3446" activeColor="#ffffff" shape="circle" dotSize={5} gap={18} proximity={140} strength={1} bounce={0.6} tension={0.4} returnDuration={0.8} shockRadius={320} shockStrength={5} swell={0.8} stretch={0.5} glow={0.5} fade={0} intro opacity={1} mouseInteraction clickShock /></div> : null}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-[1] opacity-[0.08] mix-blend-multiply"
          style={{
            backgroundImage:
              "linear-gradient(116deg, transparent 8%, rgba(139, 92, 246, 0.9) 24%, transparent 37%), linear-gradient(72deg, transparent 42%, rgba(167, 139, 250, 0.8) 54%, transparent 68%), linear-gradient(132deg, transparent 61%, rgba(124, 58, 237, 0.75) 73%, transparent 84%), radial-gradient(ellipse at 26% 42%, rgba(196, 181, 253, 0.7), transparent 42%)",
            filter: "blur(22px)",
          }}
        />
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-[2] bg-gradient-to-b from-white/10 via-white/5 to-white/25" />
        <Link to={brandHref} aria-label={brandHref === "/" ? "Kairos home" : "Kairos onboarding"} className="relative z-10 inline-flex w-fit max-w-full items-center rounded-md bg-white px-3 py-2.5 text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
          <FullLogo linked={false} />
        </Link>
        <div className="relative z-10 min-w-0 max-w-xl py-5 lg:py-16">
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.22em] text-[#77717c] lg:mb-5 lg:text-xs">
            Your academic workspace
          </p>
          <h1 className="max-w-lg break-words text-2xl font-medium leading-tight tracking-[-0.04em] text-[#343238] sm:text-3xl lg:text-4xl xl:text-5xl">
            {asideTitle}
          </h1>
        </div>
        <div className="relative z-10 hidden items-center justify-between gap-4 text-xs text-[#77717c] lg:flex">
          <span>© {new Date().getFullYear()} Kairos</span>
          <span>Learn. Teach. Belong.</span>
        </div>
      </aside>

      <section className="flex min-h-[calc(100svh-230px)] min-w-0 flex-col px-4 py-5 sm:px-8 sm:py-8 lg:min-h-screen lg:px-10 xl:px-16">
        <div className="flex min-w-0 flex-1 items-center justify-center py-7 sm:py-8 lg:py-12">
          <div className="w-full min-w-0 max-w-md">{children}</div>
        </div>
        {footer ? <footer className="mx-auto w-full min-w-0 max-w-md break-words pb-2 text-center text-sm text-muted-foreground">{footer}</footer> : null}
      </section>
    </main>
  );
}
