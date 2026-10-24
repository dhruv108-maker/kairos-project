import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowRight, BookOpenCheck, BriefcaseBusiness, CalendarClock, CheckCircle2, ClipboardCheck, GraduationCap, Users, AlertCircle, Building2, ShieldCheck } from "lucide-react";
import { Link } from "react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/context/auth/AuthContext";
import { apiRequest, ApiError, getRoleDashboard } from "@/api/kairos-client";

type ReportRequirement = { requirement: { id: string; title: string; description?: string | null; due_date?: string | null; is_required: boolean }; submission_status?: string | null };
type DashboardPayload = {
  student?: { full_name?: string; name?: string };
  internships?: { applications?: number; placements?: number };
  reports?: { total?: number; pending_review?: number; completed_evaluations?: number };
  portfolio?: { completeness?: { percentage?: number; completed?: number; total?: number } };
  placements_supervised?: number; reports_pending_review?: number; active_mentorships?: number; pending_assessment_assignments?: number;
  students?: number; faculty?: number; schools?: number; departments?: number; placements?: number; active_assessment_campaigns?: number;
};
type Metric = { label: string; value: number | string; note: string; icon: typeof Activity };
const fmt = (value?: number) => typeof value === "number" ? value.toLocaleString() : "—";
const dateLabel = (value?: string | null) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value)) : "No date set";
const roleOf = (roles: string[]) => {
  const normalized = roles.map((r) => r.toUpperCase());
  if (normalized.includes("STUDENT")) return "student";
  if (normalized.includes("FACULTY")) return "faculty";
  if (normalized.includes("RECRUITER") || normalized.includes("EMPLOYER") || normalized.includes("EMPLOYER_REPRESENTATIVE")) return "recruiter";
  if (normalized.includes("INSTITUTION_ADMIN") || normalized.includes("INSTITUTION_ADMINISTRATOR") || normalized.includes("HIGHER_AUTHORITY")) return "authority";
  if (normalized.includes("PLATFORM_ADMIN")) return "platform";
  return "unknown";
};
const statusLabel = (status?: string | null) => (status || "Not started").replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

const MetricCard = ({ metric, loading }: { metric: Metric; loading: boolean }) => {
  const Icon = metric.icon;
  return <Card className="rounded-xl border-border/80 shadow-none transition-colors hover:border-primary/30">
    <CardContent className="flex items-start justify-between gap-3 p-5">
      <div className="min-w-0"><p className="text-sm font-medium text-muted-foreground">{metric.label}</p>{loading ? <Skeleton className="mt-3 h-8 w-20" /> : <p className="mt-2 text-3xl font-semibold tracking-tight tabular-nums">{metric.value}</p>}<p className="mt-2 text-xs text-muted-foreground">{metric.note}</p></div>
      <span className="rounded-lg border border-primary/15 bg-primary/5 p-2.5 text-primary"><Icon className="h-5 w-5" aria-hidden="true" /></span>
    </CardContent>
  </Card>;
};

const SectionHeading = ({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) => <div className="mb-4"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">{eyebrow}</p><h2 className="mt-1 text-lg font-semibold tracking-tight">{title}</h2><p className="mt-1 text-sm text-muted-foreground">{description}</p></div>;

const ModernDashboard = () => {
  const { account } = useAuth();
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [requirements, setRequirements] = useState<ReportRequirement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [requirementsError, setRequirementsError] = useState("");
  const role = roleOf(account?.roles ?? []);
  const firstName = account?.full_name?.trim().split(/\s+/)[0] || "there";

  useEffect(() => {
    let active = true;
    if (!account) { setIsLoading(false); return () => { active = false; }; }
    setIsLoading(true); setError(""); setRequirementsError("");
    const dashboard = role === "recruiter" || role === "unknown" ? Promise.resolve(null) : getRoleDashboard(account) as Promise<DashboardPayload | null>;
    dashboard.then((result) => { if (active) setData(result); })
      .catch((err: unknown) => { if (active) setError(err instanceof Error ? err.message : "Unable to load overview data."); })
      .finally(() => { if (active) setIsLoading(false); });
    if (role === "student") {
      apiRequest<{ items: ReportRequirement[] }>("/reports/requirements/me")
        .then((result) => { if (active) setRequirements(result.items ?? []); })
        .catch((err: unknown) => { if (active) setRequirementsError(err instanceof Error ? err.message : "Report requirements are unavailable."); });
    }
    return () => { active = false; };
  }, [account, role]);

  const metrics: Metric[] = useMemo(() => {
    if (role === "student") return [
      { label: "Applications", value: fmt(data?.internships?.applications), note: "Internship applications recorded", icon: BriefcaseBusiness },
      { label: "Placements", value: fmt(data?.internships?.placements), note: "Recorded internship placements", icon: GraduationCap },
      { label: "Reports", value: fmt(data?.reports?.total), note: "Your report submissions", icon: BookOpenCheck },
      { label: "Needs attention", value: fmt(data?.reports?.pending_review), note: "Reports in active workflow", icon: ClipboardCheck },
    ];
    if (role === "faculty") return [
      { label: "Placements supervised", value: fmt(data?.placements_supervised), note: "Placement records assigned to you", icon: Users },
      { label: "Reports to review", value: fmt(data?.reports_pending_review), note: "Reported by the current dashboard API", icon: ClipboardCheck },
      { label: "Active mentorships", value: fmt(data?.active_mentorships), note: "Active mentorship records", icon: GraduationCap },
      { label: "Assessments pending", value: fmt(data?.pending_assessment_assignments), note: "Assigned assessment work", icon: BookOpenCheck },
    ];
    if (role === "authority" || role === "platform") return [
      { label: "Students", value: fmt(data?.students), note: "Profiles in accessible institution scope", icon: GraduationCap },
      { label: "Faculty", value: fmt(data?.faculty), note: "Faculty profiles in scope", icon: Users },
      { label: "Departments", value: fmt(data?.departments), note: "Academic departments", icon: Building2 },
      { label: "Placements", value: fmt(data?.placements), note: "Recorded internship placements", icon: BriefcaseBusiness },
    ];
    return [];
  }, [data, role]);

  const title = role === "student" ? "Student overview" : role === "faculty" ? "Faculty overview" : role === "authority" || role === "platform" ? "Institution overview" : role === "recruiter" ? "Recruiter overview" : "Overview";
  const intro = role === "student" ? "Your academic and internship responsibilities, in one place." : role === "faculty" ? "Your supervision workload and assigned academic responsibilities." : role === "authority" || role === "platform" ? "A grounded view of the academic operations available to your account." : role === "recruiter" ? "Your employer-side recruitment workspace and upcoming responsibilities." : "Your Kairos workspace and the features available to your account.";

  return <main className="mx-auto w-full max-w-7xl space-y-8 pb-8">
    <section className="flex flex-col justify-between gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end">
      <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">KAIROS / WORKSPACE</p><h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-[2.15rem]">{title}</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{intro}</p><p className="mt-3 text-sm">Good to see you, <span className="font-semibold">{firstName}</span>.</p></div>
      <div className="flex items-center gap-2 self-start rounded-full border border-border bg-background px-3 py-1.5 text-xs text-muted-foreground sm:self-auto"><span className="h-2 w-2 rounded-full bg-teal-600" /> Signed in as {role === "unknown" ? "member" : role === "authority" ? "higher authority" : role}</div>
    </section>

    {error && <div role="alert" className="flex items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" /><div><p className="font-medium text-destructive">Overview data could not be loaded</p><p className="mt-1 text-muted-foreground">{error}</p><Button variant="outline" size="sm" className="mt-3" onClick={() => window.location.reload()}>Try again</Button></div></div>}

    {metrics.length > 0 && <section aria-labelledby="summary-heading"><SectionHeading eyebrow="At a glance" title="Your current snapshot" description="Numbers are loaded from the authenticated Kairos API; unavailable values are not replaced with estimates."/><h2 id="summary-heading" className="sr-only">Your current snapshot</h2><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{metrics.map((metric) => <MetricCard key={metric.label} metric={metric} loading={isLoading} />)}</div></section>}

    {role === "student" && <section><SectionHeading eyebrow="My work" title="Report requirements" description="Check required submissions and due dates, and follow up on work that needs attention."/>
      {requirementsError && <p role="alert" className="mb-3 rounded-lg border border-destructive/30 p-3 text-sm text-destructive">{requirementsError}</p>}
      <Card className="rounded-xl border-border/80 shadow-none"><CardContent className="p-0">
        {isLoading && requirements.length === 0 ? <div className="space-y-3 p-5"><Skeleton className="h-5 w-1/3"/><Skeleton className="h-12 w-full"/><Skeleton className="h-12 w-full"/></div> : requirements.length ? <div className="divide-y divide-border">{requirements.map(({ requirement, submission_status }) => <div key={requirement.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><p className="font-medium">{requirement.title}</p><Badge variant={requirement.is_required ? "default" : "secondary"}>{requirement.is_required ? "Required" : "Optional"}</Badge></div>{requirement.description && <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{requirement.description}</p>}<p className="mt-2 text-xs text-muted-foreground">Due {dateLabel(requirement.due_date)}</p></div><div className="flex items-center gap-3 sm:justify-end"><Badge variant="outline">{statusLabel(submission_status)}</Badge></div></div>)}</div> : <div className="p-8 text-center"><CheckCircle2 className="mx-auto h-8 w-8 text-primary" /><p className="mt-3 font-medium">You’re all caught up</p><p className="mt-1 text-sm text-muted-foreground">No report requirements were returned for your account.</p></div>}
      </CardContent></Card>
    </section>}

    {(role === "faculty" || role === "authority" || role === "platform") && <section className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
      <Card className="rounded-xl border-border/80 shadow-none"><CardHeader><div className="flex items-start gap-3"><span className="rounded-lg border border-primary/15 bg-primary/5 p-2 text-primary"><ClipboardCheck className="h-5 w-5"/></span><div><CardTitle className="text-base">{role === "faculty" ? "Review workload" : "Operational priorities"}</CardTitle><CardDescription className="mt-1">{role === "faculty" ? "Use the report and assessment modules to continue work assigned to you." : "Review the institutional workflows available to your permissions."}</CardDescription></div></div></CardHeader><CardContent><p className="text-sm leading-6 text-muted-foreground">{role === "faculty" ? "The current API provides aggregate pending-review counts, but no dedicated faculty review-queue listing was found during this phase audit. A row-level queue should be connected when an authorized endpoint is available." : "Institutional report requirements and recruitment-drive management have backend routes. The current overview endpoint does not yet return a complete deadline and compliance queue."}</p>{role !== "faculty" && <Button asChild variant="outline" className="mt-4"><Link to="/pages/tables">Explore available workspace</Link></Button>}</CardContent></Card>
      <Card className="rounded-xl border-border/80 shadow-none"><CardHeader><CardTitle className="text-base">Workspace access</CardTitle><CardDescription>Identity and role from your active session</CardDescription></CardHeader><CardContent className="space-y-3 text-sm"><div><p className="text-muted-foreground">Account</p><p className="mt-1 break-all font-medium">{account?.email}</p></div><div><p className="text-muted-foreground">Assigned roles</p><div className="mt-1 flex flex-wrap gap-1.5">{account?.roles.map((r) => <Badge key={r} variant="secondary">{r.replaceAll("_", " ")}</Badge>)}</div></div></CardContent></Card>
    </section>}

    {role === "recruiter" && <section className="grid gap-4 lg:grid-cols-[1.4fr_1fr]"><Card className="rounded-xl border-border/80 shadow-none"><CardHeader><div className="flex items-center gap-3"><span className="rounded-lg border border-primary/15 bg-primary/5 p-2 text-primary"><CalendarClock className="h-5 w-5"/></span><div><CardTitle className="text-base">Interviews and offers</CardTitle><CardDescription className="mt-1">Employer-side recruitment workflows</CardDescription></div></div></CardHeader><CardContent><p className="text-sm leading-6 text-muted-foreground">Kairos supports organization-scoped interview scheduling, interview status updates, offers, and offer withdrawal. A recruiter overview feed cannot be populated safely yet because the authenticated account response does not expose the employer organization context or a consolidated interview/offer listing endpoint.</p><div className="mt-4 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">No recruitment records are displayed here until an authorized organization-scoped data source is available.</div></CardContent></Card><Card className="rounded-xl border-border/80 shadow-none"><CardHeader><CardTitle className="text-base">Recruiter workspace</CardTitle><CardDescription>Authenticated account</CardDescription></CardHeader><CardContent className="space-y-3 text-sm"><div><p className="text-muted-foreground">Name</p><p className="mt-1 font-medium">{account?.full_name}</p></div><div><p className="text-muted-foreground">Email</p><p className="mt-1 break-all font-medium">{account?.email}</p></div><div className="flex items-center gap-2 text-muted-foreground"><ShieldCheck className="h-4 w-4"/> Organization-scoped access remains enforced by the API.</div></CardContent></Card></section>}

    {(role === "unknown" || (role === "authority" || role === "platform") && !data && !isLoading && !error) && <Card className="rounded-xl border-border/80 shadow-none"><CardContent className="flex flex-col items-start gap-3 p-6 sm:flex-row"><Building2 className="h-6 w-6 text-primary"/><div><h2 className="font-semibold">Institution context required</h2><p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">The current account response does not include a selected institution. Institution metrics are shown only when the API can resolve an authorized institution scope; this page will not guess or combine scopes.</p></div></CardContent></Card>}

    <footer className="flex flex-col gap-2 border-t border-border/80 pt-4 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between"><span>Kairos · Role-aware workspace</span><span>Only data returned by authorized API endpoints is shown.</span></footer>
  </main>;
};

export default ModernDashboard;
