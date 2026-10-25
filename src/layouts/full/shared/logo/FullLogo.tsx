import { Link } from "react-router";
import { GraduationCap } from "lucide-react";

interface FullLogoProps {
  /** Render only the visual brand when a parent link provides navigation. */
  linked?: boolean;
}

const LogoMark = () => (
  <>
    <span aria-hidden="true" className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
      <GraduationCap className="size-[18px]" />
    </span>
    <span className="text-[15px] font-semibold tracking-tight text-foreground group-data-[collapsible=icon]:hidden">Kairos</span>
  </>
);

const FullLogo = ({ linked = true }: FullLogoProps) => (
  linked ? (
    <Link to="/" aria-label="Kairos home" className="inline-flex min-w-0 items-center gap-2 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
      <LogoMark />
    </Link>
  ) : (
    <span className="inline-flex min-w-0 items-center gap-2">
      <LogoMark />
    </span>
  )
);

export default FullLogo;
