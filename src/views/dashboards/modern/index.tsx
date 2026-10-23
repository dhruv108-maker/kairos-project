import { useEffect, useState } from "react";
import { Activity, BookOpenCheck, BriefcaseBusiness, ClipboardCheck, GraduationCap, Users } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/auth/AuthContext";
import { getRoleDashboard } from "@/api/kairos-client";

type DashboardPayload = {
  internships?: { applications?: number; placements?: number };
  reports?: { total?: number; pending_review?: number; completed_evaluations?: number };
  portfolio?: { completeness?: unknown };
  placements_supervised?: number;
  reports_pending_review?: number;
  active_mentorships?: number;
  pending_assessment_assignments?: number;
};

type Metric = { label: string; value: string | number; description: string; icon: typeof Activity };

const numberValue = (value: unknown) => typeof value === "number" ? value.toLocaleString() : "—";

const ModernDashboard = () => {
  const { account } = useAuth();
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    if (!account) {
      setIsLoading(false);
      return () => { active = false; };
    }
    setIsLoading(true);
    setError("");
    getRoleDashboard(account)
      .then((result) => {
        if (active) setData(result as DashboardPayload | null);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : "Unable to load dashboard data.");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => { active = false; };
  }, [account]);

  const roles = account?.roles.map((role) => role.toUpperCase()) ?? [];
  const isStudent = roles.includes("STUDENT");
  const isFaculty = roles.includes("FACULTY");
  const roleLabel = isStudent ? "Student" : isFaculty ? "Faculty" : "Institute administrator";

  const metrics: Metric[] = isStudent ? [
    { label: "Internship applications", value: numberValue(data?.internships?.applications), description: "Applications submitted", icon: BriefcaseBusiness },
    { label: "Active placements", value: numberValue(data?.internships?.placements), description: "Internship placements", icon: GraduationCap },
    { label: "Reports submitted", value: numberValue(data?.reports?.total), description: "Your internship reports", icon: BookOpenCheck },
    { label: "Pending review", value: numberValue(data?.reports?.pending_review), description: "Reports awaiting review", icon: ClipboardCheck },
  ] : isFaculty ? [
    { label: "Students supervised", value: numberValue(data?.placements_supervised), description: "Internship placements", icon: Users },
    { label: "Reports to review", value: numberValue(data?.reports_pending_review), description: "Awaiting your review", icon: ClipboardCheck },
    { label: "Active mentorships", value: numberValue(data?.active_mentorships), description: "Current student mentorships", icon: GraduationCap },
    { label: "Assessments pending", value: numberValue(data?.pending_assessment_assignments), description: "Assigned assessments", icon: BookOpenCheck },
  ] : [];

  return (
    <div className="space-y-6 pb-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-primary">KAIROS WORKSPACE</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Welcome back, {account?.full_name?.split(" ")[0] ?? "there"}</h1>
          <p className="mt-2 text-muted-foreground">Your {roleLabel.toLowerCase()} overview and academic activity.</p>
        </div>
        <div className="inline-flex w-fit items-center gap-2 rounded-full border bg-background px-3 py-1.5 text-sm text-muted-foreground">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          Connected to Kairos API
        </div>
      </div>

      {error && <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">{error}</div>}

      {metrics.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <Card key={metric.label} className="rounded-xl">
                <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
                  <div className="space-y-1">
                    <CardDescription>{metric.label}</CardDescription>
                    <CardTitle className="text-3xl font-semibold tracking-tight">{isLoading ? "…" : metric.value}</CardTitle>
                  </div>
                  <div className="rounded-lg bg-primary/10 p-2.5 text-primary"><Icon className="h-5 w-5" /></div>
                </CardHeader>
                <CardContent><p className="text-xs text-muted-foreground">{metric.description}</p></CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card className="rounded-xl">
          <CardHeader>
            <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary"><Activity className="h-5 w-5" /></div>
            <CardTitle>Institution overview</CardTitle>
            <CardDescription>
              {isLoading
                ? "Loading your workspace data…"
                : "Your account is authenticated. Institution-level metrics require an institution context, which the current /auth/me response does not include. This view will be connected when the institution selection/profile endpoint is available."}
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="rounded-xl lg:col-span-2">
          <CardHeader>
            <CardTitle>Next steps</CardTitle>
            <CardDescription>Keep your Kairos workspace up to date.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <div className="flex items-start gap-3"><span className="mt-1 h-2 w-2 rounded-full bg-primary" /><p>Review your profile and verify that your institutional details are correct.</p></div>
            <div className="flex items-start gap-3"><span className="mt-1 h-2 w-2 rounded-full bg-primary" /><p>Use the dashboard metrics to track internships, reports, mentorships, and assessments relevant to your role.</p></div>
          </CardContent>
        </Card>
        <Card className="rounded-xl">
          <CardHeader>
            <CardTitle>Workspace access</CardTitle>
            <CardDescription>Signed-in account</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div><p className="text-muted-foreground">Name</p><p className="font-medium">{account?.full_name}</p></div>
            <div><p className="text-muted-foreground">Email</p><p className="break-all font-medium">{account?.email}</p></div>
            <div><p className="text-muted-foreground">Role</p><p className="font-medium">{account?.roles.join(", ") || "No role assigned"}</p></div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ModernDashboard;
