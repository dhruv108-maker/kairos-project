import { Link } from "react-router";
import { GraduationCap } from "lucide-react";

const FullLogo = () => (
  <Link to="/" className="inline-flex items-center gap-2.5">
    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
      <GraduationCap className="h-5 w-5" />
    </span>
    <span className="text-lg font-semibold tracking-tight text-foreground">Kairos</span>
  </Link>
);

export default FullLogo;
