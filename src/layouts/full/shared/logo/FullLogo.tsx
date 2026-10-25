import { Link } from "react-router";
import { GraduationCap } from "lucide-react";

interface FullLogoProps {
  /** Render only the visual brand when a parent link provides navigation. */
  linked?: boolean;
}

const LogoMark = () => (
  <>
    <span aria-hidden="true" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
      <GraduationCap className="h-5 w-5" />
    </span>
    <span className="text-lg font-semibold tracking-tight text-foreground group-data-[collapsible=icon]:hidden">Kairos</span>
  </>
);

const FullLogo = ({ linked = true }: FullLogoProps) => (
  linked ? (
    <Link to="/" aria-label="Kairos home" className="inline-flex items-center gap-2.5 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
      <LogoMark />
    </Link>
  ) : (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark />
    </span>
  )
);

export default FullLogo;
