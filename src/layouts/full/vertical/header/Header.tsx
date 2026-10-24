import { useLocation } from "react-router";
import { useSidebar } from "src/components/ui/sidebar";
import { Button } from "src/components/ui/button";
import { PanelLeft, ChevronRight } from "lucide-react";
import { Separator } from "src/components/ui/separator";
import { cn } from "src/lib/utils";
import FullLogo from "../../shared/logo/FullLogo";
import Profile from "./Profile";
import LightDark from "./Light-Dark";

const routeTitles: Record<string, string> = {
  "/": "Overview",
  "/dashboards/modern": "Overview",
  "/pages/user-profile": "My profile",
  "/pages/tables": "Data tables",
  "/pages/form": "Forms",
};

const Header = () => {
  const { toggleSidebar } = useSidebar();
  const location = useLocation();
  const title = routeTitles[location.pathname] ?? "Kairos workspace";

  return (
    <header className={cn("sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur-sm")}>
      <nav aria-label="Workspace header" className="mx-auto flex min-h-14 items-center justify-between gap-3 px-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <div className="block lg:hidden"><FullLogo /></div>
          <Button variant="ghost" size="icon" className="shrink-0 rounded-lg" onClick={toggleSidebar} aria-label="Toggle navigation sidebar">
            <PanelLeft size={20} aria-hidden="true" />
          </Button>
          <Separator orientation="vertical" className="hidden h-5 sm:block" />
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs text-muted-foreground"><span>Kairos</span><ChevronRight className="h-3 w-3" aria-hidden="true" /><span aria-current="page" className="truncate">{title}</span></div>
            <p className="truncate text-sm font-semibold">{title}</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <LightDark />
          <Profile />
        </div>
      </nav>
    </header>
  );
};

export default Header;
