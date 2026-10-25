import { FC } from "react";
import { Navigate, Outlet } from "react-router";
import Sidebar from "./vertical/sidebar/Sidebar";
import Header from "./vertical/header/Header";
import { SidebarInset, SidebarProvider } from "src/components/ui/sidebar";
import { cn } from "src/lib/utils";
import Footer from "./shared/footer/Footer";
import { useAuth } from "@/context/auth/AuthContext";

type FullLayoutProps = {
  allowAnonymous?: boolean;
};

const FullLayout: FC<FullLayoutProps> = ({ allowAnonymous = false }) => {
  const { account, isLoading } = useAuth();

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">Loading your Kairos workspace…</div>;
  }
  if (!account && !allowAnonymous) return <Navigate to="/auth/auth2/login" replace />;

  return (
    <SidebarProvider defaultOpen={true} style={{ "--sidebar-width-icon": "52px" } as React.CSSProperties}>
      <Sidebar />
      <SidebarInset className="min-h-svh min-w-0 overflow-x-clip bg-background">
        <Header />
        <div className="flex flex-1 flex-col gap-6 px-4 py-5 sm:px-6 sm:py-6 lg:px-8">
          <div className={cn("w-full mx-auto", "container")}>
            <div className="min-h-[calc(100svh-9rem)]"><Outlet /></div>
            <div className="mt-8 border-t border-border/70 pt-5"><Footer /></div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
};

export default FullLayout;
