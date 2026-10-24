import { useEffect, useState } from "react";
import { Link } from "react-router";
import { ArrowLeft, BriefcaseBusiness, CalendarDays, RefreshCw, Search } from "lucide-react";
import { ApiError, apiRequest } from "@/api/kairos-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

type ApplicationItem = {
  id: string;
  status: string;
  applied_at?: string | null;
  opportunity: {
    id: string;
    title: string;
    location?: string | null;
    opportunity_type?: string | null;
    employment_type?: string | null;
    company?: { id?: string; name?: string | null } | null;
    provider?: { company_name?: string | null } | null;
  };
};
type ApplicationsResponse = { items: ApplicationItem[] };

const statusStyle: Record<string, string> = {
  APPLIED: "border-sky-200 bg-sky-50 text-sky-800",
  SHORTLISTED: "border-teal-200 bg-teal-50 text-teal-800",
  OFFERED: "border-violet-200 bg-violet-50 text-violet-800",
  REJECTED: "border-rose-200 bg-rose-50 text-rose-800",
  WITHDRAWN: "border-slate-200 bg-slate-100 text-slate-700",
};
const dateLabel = (value?: string | null) => {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(date);
};

export default function JobApplications() {
  const [items, setItems] = useState<ApplicationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    apiRequest<ApplicationsResponse>("/internships/applications/me", { signal: controller.signal })
      .then((response) => { if (!controller.signal.aborted) setItems(response.items || []); })
      .catch((err) => {
        if (controller.signal.aborted) return;
        if (err instanceof ApiError && err.status === 401) setError("Sign in to view your applications.");
        else if (err instanceof ApiError && err.status === 403) setError("My applications is available to student accounts.");
        else setError(err instanceof Error ? err.message : "We couldn't load your applications.");
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [reload]);

  return <main className="min-h-[70vh] bg-[#fafbfc] px-4 py-7 text-slate-900 sm:px-6 lg:px-8">
    <div className="mx-auto max-w-5xl">
      <Link to="/jobs" className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-teal-800"><ArrowLeft className="h-4 w-4" />Back to opportunities</Link>
      <div className="mt-6 flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-xs font-semibold uppercase tracking-[0.15em] text-teal-800">Your career activity</p><h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-slate-950">My applications</h1><p className="mt-2 text-sm text-slate-600">Track the status of your Kairos internship applications.</p></div>
        <Button asChild className="rounded-xl bg-teal-800 text-white hover:bg-teal-900"><Link to="/jobs"><Search className="mr-2 h-4 w-4" />Explore roles</Link></Button>
      </div>
      <Separator className="my-6" />
      {loading && <div className="space-y-3">{[1, 2, 3].map((n) => <Card key={n} className="rounded-2xl p-5"><Skeleton className="h-5 w-2/3" /><Skeleton className="mt-3 h-4 w-1/3" /><Skeleton className="mt-5 h-8 w-28" /></Card>)}</div>}
      {!loading && error && <Card className="rounded-2xl border-rose-200 p-6"><h2 className="font-semibold">Applications unavailable</h2><p className="mt-2 text-sm leading-6 text-slate-600">{error}</p>{error.includes("Sign in") && <Button asChild className="mt-4 bg-teal-800 hover:bg-teal-900"><Link to="/auth/auth2/login">Sign in</Link></Button>}{!error.includes("Sign in") && <Button variant="outline" className="mt-4" onClick={() => setReload((v) => v + 1)}><RefreshCw className="mr-2 h-4 w-4" />Try again</Button>}</Card>}
      {!loading && !error && items.length === 0 && <Card className="rounded-2xl border-dashed border-slate-300 p-10 text-center"><BriefcaseBusiness className="mx-auto h-8 w-8 text-slate-300" /><h2 className="mt-4 text-lg font-semibold">No applications yet</h2><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">When you apply to an opportunity through Kairos, its current status will appear here.</p><Button asChild className="mt-5 rounded-xl bg-teal-800 hover:bg-teal-900"><Link to="/jobs">Explore opportunities</Link></Button></Card>}
      {!loading && !error && items.length > 0 && <div className="space-y-3">{items.map((item) => {
        const opportunity = item.opportunity;
        const status = (item.status || "APPLIED").toUpperCase();
        const company = opportunity.company?.name || opportunity.provider?.company_name || "Employer";
        return <Card key={item.id} className="rounded-2xl border-slate-200 bg-white p-5 transition hover:border-teal-200 hover:shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-teal-50 text-teal-800"><BriefcaseBusiness className="h-5 w-5" /></div>
            <div className="min-w-0 flex-1"><h2 className="font-semibold text-slate-900">{opportunity.title}</h2><p className="mt-1 text-sm text-slate-600">{company}{opportunity.location ? " · " + opportunity.location : ""}</p><p className="mt-2 flex items-center gap-1.5 text-xs text-slate-500"><CalendarDays className="h-3.5 w-3.5" />Applied {dateLabel(item.applied_at)}</p></div>
            <div className="flex items-center justify-between gap-3 sm:flex-col sm:items-end"><Badge variant="outline" className={`rounded-full px-3 py-1 ${statusStyle[status] || "border-slate-200 bg-slate-50 text-slate-700"}`}>{status.replaceAll("_", " ")}</Badge><Link to={`/jobs?job=${encodeURIComponent(opportunity.id)}`} className="text-sm font-medium text-teal-800 hover:underline">View opportunity</Link></div>
          </div>
        </Card>;
      })}</div>}
    </div>
  </main>;
}
