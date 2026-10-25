import { useEffect, useRef, type ReactNode } from "react";
import { Link } from "react-router";
import FullLogo from "src/layouts/full/shared/logo/FullLogo";

declare global {
  interface Window {
    VANTA?: {
      FOG?: (options: Record<string, unknown>) => { destroy: () => void };
    };
    THREE?: unknown;
  }
}

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
  asideTitle,
  brandHref = "/onboarding",
  footer,
}: AuthFrameProps) {
  const effectRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = effectRef.current;
    if (!element || !window.VANTA?.FOG || !window.THREE) return;

    const effect = window.VANTA.FOG({
      el: element,
      THREE: window.THREE,
      mouseControls: true,
      touchControls: true,
      gyroControls: false,
      minHeight: 200,
      minWidth: 200,
      highlightColor: 0x087f8c,
      midtoneColor: 0x171d25,
      lowlightColor: 0x071216,
      baseColor: 0x08090b,
      blurFactor: 0.55,
      speed: 0.45,
      zoom: 0.65,
    });

    return () => effect.destroy();
  }, []);

  return (
    <main className="min-h-svh w-full min-w-0 overflow-x-clip bg-background text-foreground lg:grid lg:min-h-screen lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
      <aside className="relative flex min-h-[230px] min-w-0 flex-col justify-between overflow-hidden bg-[#08090b] px-5 py-5 text-white sm:min-h-[260px] sm:px-8 sm:py-7 lg:min-h-screen lg:px-10 lg:py-9 xl:px-14 xl:py-11">
        <div ref={effectRef} aria-hidden="true" className="pointer-events-none absolute inset-0 z-0" />
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-[1] bg-gradient-to-b from-black/25 via-black/20 to-black/65" />
        <Link to={brandHref} aria-label={brandHref === "/" ? "Kairos home" : "Kairos onboarding"} className="relative z-10 inline-flex w-fit max-w-full items-center rounded-md bg-white px-3 py-2.5 text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
          <FullLogo linked={false} />
        </Link>
        <div className="relative z-10 min-w-0 max-w-xl py-5 lg:py-16">
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.22em] text-white/65 lg:mb-5 lg:text-xs">
            Your academic workspace
          </p>
          <h1 className="max-w-lg break-words text-2xl font-medium leading-tight tracking-[-0.04em] text-white sm:text-3xl lg:text-4xl xl:text-5xl">
            {asideTitle}
          </h1>
        </div>
        <div className="relative z-10 hidden items-center justify-between gap-4 text-xs text-white/55 lg:flex">
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
