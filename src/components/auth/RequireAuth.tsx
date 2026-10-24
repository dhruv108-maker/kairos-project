import { Navigate, useLocation } from "react-router";
import { useAuth } from "@/context/auth/AuthContext";

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { account, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div role="status" className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">Checking your session…</div>;
  }

  if (!account) {
    return <Navigate to="/auth/auth2/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
