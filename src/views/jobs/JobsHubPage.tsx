import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams, useParams } from "react-router";
import {
  ArrowLeft, ArrowUpRight, BriefcaseBusiness, Building2, CalendarDays,
  CheckCircle2, ChevronLeft, ChevronRight, CircleAlert, ExternalLink,
  MapPin, RefreshCw, Search, SlidersHorizontal, Sparkles, Users, X,
} from "lucide-react";
import { apiRequest, ApiError, type KairosAccount } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Company = { id?: string | null; name?: string | null; website?: string | null };
type Opportunity = {
  id: string;
  title: string;
  summary?: string | null;
  description?: string | null;
  location?: string | null;
  application_deadline?: string | null;
  starts_on?: string | null;
  ends_on?: string | null;
  lifecycle_status?: string | null;
  opportunity_type?: string | null;
  employment_type?: string | null;
  work_mode?: string | null;
  department?: string | null;
  experience_min_years?: number | string | null;
  experience_max_years?: number | string | null;
  compensation_min?: number | string | null;
  compensation_max?: number | string | null;
  compensation_currency?: string | null;
  compensation_period?: string | null;
  compensation_visible?: boolean;
  required_skills?: string[] | null;
  preferred_skills?: string[] | null;
  education_requirements?: string | null;
  public_application_url?: string | null;
  created_at?: string | null;
  company?: Company | null;
};
type PageResult = { items: Opportunity[]; limit: number; offset: number };
type Application = {
  id: string;
  opportunity_id?: string;
  status: string;
  applied_at?: string | null;
  opportunity?: Opportunity & { company_name?: string | null };
};

type CampusDrive = {
  id: string;
  name: string;
  description?: string | null;
  starts_on?: string | null;
  ends_on?: string | null;
  status: string;
  eligibility?: { status: string; reason_codes: string[] };
};
type CampusOpportunity = Opportunity & {
  eligibility?: { status: string; reason_codes: string[] };
};

const PAGE_SIZE = 12;
const TYPES = [
  { label: "All opportunities", value: "" },
  { label: "Internships", value: "INTERNSHIP" },
  { label: "Full-time jobs", value: "JOB" },
];
const MODES = [
  { label: "Any workplace", value: "" },
  { label: "On-site", value: "ONSITE" },
  { label: "Hybrid", value: "HYBRID" },
  { label: "Remote", value: "REMOTE" },
];

function dateLabel(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
function salaryLabel(job: Opportunity) {
  if (!job.compensation_visible || (job.compensation_min == null && job.compensation_max == null)) return null;
  const currency = job.compensation_currency || "INR";
  const format = (value: string | number) => new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(Number(value));
  const range = job.compensation_min != null && job.compensation_max != null
    ? `${format(job.compensation_min)}–${format(job.compensation_max)}`
    : format((job.compensation_min ?? job.compensation_max) as string | number);
  return `${currency} ${range}${job.compensation_period ? ` / ${job.compensation_period.toLowerCase()}` : ""}`;
}
function companyInitials(name?: string | null) {
  return (name || "Kairos").trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}
function opportunityKind(job: Opportunity) {
  return (job.opportunity_type || job.employment_type || "OPPORTUNITY").replace(/_/g, " ").toLowerCase();
}
function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Your session has expired. Sign in again to continue.";
    if (error.status === 403) return "You don’t have permission to access this information.";
    if (error.status === 404) return "This opportunity is no longer available.";
    if (error.status === 409) return "This action conflicts with the current application state. Refresh and try again.";
    if (error.status === 422) return error.message;
    return error.message;
  }
  return "We couldn’t connect to Kairos. Check your connection and try again.";
}

function CompanyMark({ name }: { name?: string | null }) {
  return <div aria-hidden="true" className="flex size-12 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-sm font-semibold tracking-wide text-slate-700">{companyInitials(name)}</div>;
}

function OpportunityCard({ job, selected, onSelect }: { job: Opportunity; selected: boolean; onSelect: () => void }) {
  const company = job.company?.name || "Employer";
  const salary = salaryLabel(job);
  return (
    <article className={`group rounded-2xl border bg-white p-4 transition hover:border-teal-300 hover:shadow-[0_8px_24px_rgba(15,23,42,0.06)] focus-within:ring-2 focus-within:ring-teal-600/20 ${selected ? "border-teal-500 shadow-sm" : "border-slate-200"}`}>
      <div className="flex items-start gap-3">
        <CompanyMark name={company} />
        <div className="min-w-0 flex-1">
          <button type="button" onClick={onSelect} className="text-left font-semibold leading-5 text-slate-900 decoration-teal-600 underline-offset-4 hover:text-teal-800 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600">
            {job.title}
          </button>
          <p className="mt-1 truncate text-sm text-slate-600">{company}</p>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
            {job.location && <span className="inline-flex items-center gap-1"><MapPin className="size-3.5" />{job.location}</span>}
            {job.work_mode && <span className="inline-flex items-center gap-1"><Building2 className="size-3.5" />{job.work_mode.toLowerCase()}</span>}
          </div>
        </div>
        <Badge variant="outline" className="shrink-0 border-slate-200 bg-slate-50 font-medium capitalize text-slate-600">{opportunityKind(job)}</Badge>
      </div>
      <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-600">{job.summary || job.description || "Open the opportunity to review the full role details and application instructions."}</p>
      {(job.required_skills?.length || salary || job.application_deadline) ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {salary && <span className="text-xs font-medium text-slate-700">{salary}</span>}
          {(job.required_skills || []).slice(0, 3).map((skill) => <Badge key={skill} variant="secondary" className="font-normal text-slate-600">{skill}</Badge>)}
          {job.application_deadline && <span className="ml-auto inline-flex items-center gap-1 text-xs text-slate-500"><CalendarDays className="size-3.5" />Closes {dateLabel(job.application_deadline)}</span>}
        </div>
      ) : null}
      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
        <span className="text-xs text-slate-500">{job.created_at ? `Posted ${dateLabel(job.created_at)}` : "Opportunity details available"}</span>
        <Button variant={selected ? "secondary" : "outline"} size="sm" onClick={onSelect}>View details <ArrowUpRight className="size-3.5" /></Button>
      </div>
    </article>
  );
}

function DetailPanel({ job, account, appliedIds, onApply, applying }: {
  job: Opportunity; account: KairosAccount | null; appliedIds: Set<string>;
  onApply: (job: Opportunity) => void; applying: string | null;
}) {
  const company = job.company?.name || "Employer";
  const applied = appliedIds.has(job.id);
  const expired = Boolean(job.application_deadline && new Date(job.application_deadline).getTime() < Date.now());
  const externalUrl = job.public_application_url;
  const canApply = account?.roles?.some((role) => role.toUpperCase() === "STUDENT");
  const validExternal = (() => {
    if (!externalUrl) return false;
    try { const parsed = new URL(externalUrl); return parsed.protocol === "https:" || parsed.protocol === "http:"; }
    catch { return false; }
  })();
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="border-b border-slate-100 p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <CompanyMark name={company} />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-slate-600">{company}</p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-950">{job.title}</h2>
            <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500">
              {job.location && <span className="inline-flex items-center gap-1"><MapPin className="size-4" />{job.location}</span>}
              {job.work_mode && <span>{job.work_mode.toLowerCase()}</span>}
            </p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Badge variant="secondary" className="capitalize">{opportunityKind(job)}</Badge>
          {job.lifecycle_status && <Badge variant="outline">{job.lifecycle_status.toLowerCase().replace(/_/g, " ")}</Badge>}
          {salaryLabel(job) && <Badge variant="outline">{salaryLabel(job)}</Badge>}
        </div>
        <div className="mt-5 grid gap-2 sm:grid-cols-2">
          {validExternal && !expired ? (
            <a className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-teal-700 px-4 text-sm font-medium text-white transition hover:bg-teal-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2" href={externalUrl!} target="_blank" rel="noopener noreferrer">Apply on company website <ExternalLink className="size-4" /></a>
          ) : !account && !expired ? (
            <Button className="w-full bg-teal-700 text-white hover:bg-teal-800" onClick={() => window.location.assign("/auth/auth2/login")}>Sign in to apply</Button>
          ) : account && !canApply && !expired ? (
            <Button className="w-full" disabled>Student account required</Button>
          ) : canApply && !validExternal && !applied && !expired ? (
            <Button className="w-full bg-teal-700 text-white hover:bg-teal-800" disabled={applying === job.id} onClick={() => onApply(job)}>
              {applying === job.id ? "Applying…" : "Apply through Kairos"}
            </Button>
          ) : applied ? (
            <Button variant="secondary" className="w-full" onClick={() => window.location.assign("/jobs/applications")}><CheckCircle2 className="size-4" />Application submitted · View status</Button>
          ) : expired ? (
            <Button className="w-full" disabled>Application deadline passed</Button>
          ) : null}

        </div>
        {validExternal && canApply && <p className="mt-3 flex items-start gap-1.5 text-xs leading-5 text-slate-500"><ExternalLink className="mt-0.5 size-3.5 shrink-0" />You’ll leave Kairos to complete your application on the company website.</p>}
        {!validExternal && job.public_application_url && <p role="status" className="mt-3 text-xs text-amber-700">The stored external link is invalid. You can still apply through Kairos if eligible.</p>}
        {canApply && !externalUrl && !applied && !expired && <p className="mt-3 text-xs text-slate-500">Your application will be submitted to Kairos using the existing student application workflow.</p>}
      </div>
      <div className="space-y-6 p-5 sm:p-6">
        <section><h3 className="font-semibold text-slate-900">About the role</h3><p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-600">{job.description || job.summary || "The employer has not supplied a full description."}</p></section>
        {job.required_skills?.length ? <section><h3 className="font-semibold text-slate-900">Required skills</h3><div className="mt-2 flex flex-wrap gap-2">{job.required_skills.map((skill) => <Badge variant="secondary" key={skill}>{skill}</Badge>)}</div></section> : null}
        {job.preferred_skills?.length ? <section><h3 className="font-semibold text-slate-900">Preferred skills</h3><div className="mt-2 flex flex-wrap gap-2">{job.preferred_skills.map((skill) => <Badge variant="outline" key={skill}>{skill}</Badge>)}</div></section> : null}
        {job.education_requirements && <section><h3 className="font-semibold text-slate-900">Education requirements</h3><p className="mt-2 text-sm leading-6 text-slate-600">{job.education_requirements}</p></section>}
        <section className="grid gap-4 border-t border-slate-100 pt-5 sm:grid-cols-2">
          {job.application_deadline && <div><p className="text-xs font-medium uppercase tracking-wide text-slate-500">Application deadline</p><p className="mt-1 text-sm font-medium text-slate-800">{dateLabel(job.application_deadline)}</p></div>}
          {(job.experience_min_years != null || job.experience_max_years != null) && <div><p className="text-xs font-medium uppercase tracking-wide text-slate-500">Experience</p><p className="mt-1 text-sm font-medium text-slate-800">{job.experience_min_years ?? 0}{job.experience_max_years != null ? `–${job.experience_max_years}` : "+"} years</p></div>}
          {job.department && <div><p className="text-xs font-medium uppercase tracking-wide text-slate-500">Team</p><p className="mt-1 text-sm font-medium text-slate-800">{job.department}</p></div>}
          {job.starts_on && <div><p className="text-xs font-medium uppercase tracking-wide text-slate-500">Expected start</p><p className="mt-1 text-sm font-medium text-slate-800">{dateLabel(job.starts_on)}</p></div>}
        </section>
      </div>
    </div>
  );
}

export default function JobsHubPage() {
  const { account } = useAuth();
  const routeLocation = useLocation();
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState(params.get("q") || "");
  const [location, setLocation] = useState(params.get("location") || "");
  const [kind, setKind] = useState(params.get("opportunity_type") || "");
  const [mode, setMode] = useState(params.get("work_mode") || "");
  const [offset, setOffset] = useState(Number(params.get("offset") || 0));
  const [result, setResult] = useState<PageResult>({ items: [], limit: PAGE_SIZE, offset: 0 });
  const [selectedId, setSelectedId] = useState(params.get("job") || "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [applying, setApplying] = useState<string | null>(null);
  const [applicationError, setApplicationError] = useState("");
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());
  const [applicationLoading, setApplicationLoading] = useState(false);
  const [applications, setApplications] = useState<Application[]>([]);
  const [campusDrives, setCampusDrives] = useState<CampusDrive[]>([]);
  const [selectedCampusDrive, setSelectedCampusDrive] = useState<CampusDrive | null>(null);
  const [campusOpportunities, setCampusOpportunities] = useState<CampusOpportunity[]>([]);
  const navigate = useNavigate();
  const isStudent = Boolean(account?.roles?.some((role) => role.toUpperCase() === "STUDENT"));
  const isApplicationsPage = routeLocation.pathname === "/jobs/applications";
  const isCampusPage = routeLocation.pathname === "/jobs/campus";

  const loadJobs = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    const search = new URLSearchParams();
    if (query.trim()) search.set("q", query.trim());
    if (location.trim()) search.set("location", location.trim());
    if (kind) search.set("opportunity_type", kind);
    if (mode) search.set("work_mode", mode);
    search.set("limit", String(PAGE_SIZE));
    search.set("offset", String(offset));
    try {
      const data = await apiRequest<PageResult>(`/jobs?${search.toString()}`, { signal });
      setResult(data);
      setSelectedId((current) => current && data.items.some((item) => item.id === current) ? current : (data.items[0]?.id || ""));
    } catch (err) {
      if (signal?.aborted) return;
      setError(errorMessage(err));
      setResult({ items: [], limit: PAGE_SIZE, offset });
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [query, location, kind, mode, offset]);

  useEffect(() => {
    if (isApplicationsPage || isCampusPage) return;
    const controller = new AbortController();
    void loadJobs(controller.signal);
    return () => controller.abort();
  }, [loadJobs, isApplicationsPage, isCampusPage]);

  useEffect(() => {
    const next = new URLSearchParams();
    if (query.trim()) next.set("q", query.trim());
    if (location.trim()) next.set("location", location.trim());
    if (kind) next.set("opportunity_type", kind);
    if (mode) next.set("work_mode", mode);
    if (offset) next.set("offset", String(offset));
    if (selectedId) next.set("job", selectedId);
    if (next.toString() !== params.toString()) setParams(next, { replace: true });
  }, [query, location, kind, mode, offset, selectedId, params, setParams]);

  useEffect(() => {
    if (!isStudent) return;
    let active = true;
    apiRequest<{ items: Application[] }>("/modules/internships/applications/me")
      .then((data) => {
        if (!active) return;
        const items = (data.items || []).map((item) => item.opportunity?.company_name
          ? { ...item, opportunity: { ...item.opportunity, company: { name: item.opportunity.company_name } } }
          : item);
        setApplications(items);
        setAppliedIds(new Set(items.map((item) => item.opportunity_id || item.opportunity?.id).filter((id): id is string => Boolean(id))));
      })
      .catch(() => { /* Discovery remains available if application history is temporarily unavailable. */ });
    return () => { active = false; };
  }, [isStudent]);

  const selected = useMemo(() => result.items.find((job) => job.id === selectedId) || null, [result.items, selectedId]);

  const apply = async (job: Opportunity) => {
    setApplying(job.id);
    setApplicationError("");
    try {
      await apiRequest(`/modules/internships/opportunities/${encodeURIComponent(job.id)}/applications`, { method: "POST" });
      setAppliedIds((current) => new Set(current).add(job.id));
      setApplications((current) => [{ id: `pending-refresh-${job.id}`, opportunity_id: job.id, status: "APPLIED", applied_at: new Date().toISOString(), opportunity: job }, ...current]);
    } catch (err) {
      setApplicationError(errorMessage(err));
    } finally {
      setApplying(null);
    }
  };

  useEffect(() => {
    if (!isApplicationsPage || !isStudent) return;
    const controller = new AbortController();
    setApplicationLoading(true);
    apiRequest<{ items: Application[] }>("/modules/internships/applications/me", { signal: controller.signal })
      .then((data) => {
        const items = (data.items || []).map((item) => item.opportunity?.company_name
          ? { ...item, opportunity: { ...item.opportunity, company: { name: item.opportunity.company_name } } }
          : item);
        setApplications(items);
        setAppliedIds(new Set(items.map((item) => item.opportunity_id || item.opportunity?.id).filter((id): id is string => Boolean(id))));
      })
      .catch((err) => { if (!controller.signal.aborted) setApplicationError(errorMessage(err)); })
      .finally(() => { if (!controller.signal.aborted) setApplicationLoading(false); });
    return () => controller.abort();
  }, [isApplicationsPage, isStudent]);

  useEffect(() => {
    if (!isCampusPage || !isStudent) return;
    const controller = new AbortController();
    setApplicationLoading(true);
    setApplicationError("");
    apiRequest<{ items: CampusDrive[] }>("/students/recruitment-drives", { signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        setCampusDrives(data.items || []);
        setSelectedCampusDrive(null);
        setCampusOpportunities([]);
      })
      .catch((err) => { if (!controller.signal.aborted) setApplicationError(errorMessage(err)); })
      .finally(() => { if (!controller.signal.aborted) setApplicationLoading(false); });
    return () => controller.abort();
  }, [isCampusPage, isStudent]);

  useEffect(() => {
    if (!isCampusPage || !isStudent || !selectedCampusDrive) {
      setCampusOpportunities([]);
      return;
    }
    const controller = new AbortController();
    setApplicationLoading(true);
    setApplicationError("");
    apiRequest<{ items: Array<Record<string, unknown>> }>(`/students/recruitment-drives/${encodeURIComponent(selectedCampusDrive.id)}/opportunities`, { signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        const rows = data.items || [];
        setCampusOpportunities(rows.map((row) => ({
          id: String(row.id),
          title: String(row.title || "Campus opportunity"),
          summary: typeof row.summary === "string" ? row.summary : null,
          description: typeof row.description === "string" ? row.description : null,
          location: typeof row.location === "string" ? row.location : null,
          application_deadline: typeof row.application_deadline === "string" ? row.application_deadline : null,
          opportunity_type: typeof row.opportunity_type === "string" ? row.opportunity_type : null,
          employment_type: typeof row.employment_type === "string" ? row.employment_type : null,
          work_mode: typeof row.work_mode === "string" ? row.work_mode : null,
          company: typeof row.company === "string" ? { name: row.company } : null,
          eligibility: row.eligibility as CampusOpportunity["eligibility"],
        })));
      })
      .catch((err) => { if (!controller.signal.aborted) setApplicationError(errorMessage(err)); })
      .finally(() => { if (!controller.signal.aborted) setApplicationLoading(false); });
    return () => controller.abort();
  }, [isCampusPage, isStudent, selectedCampusDrive]);

  const clearFilters = () => { setQuery(""); setLocation(""); setKind(""); setMode(""); setOffset(0); };
  const runSearch = (event: FormEvent) => { event.preventDefault(); setOffset(0); void loadJobs(); };

  if ((isApplicationsPage || isCampusPage) && !isStudent) {
    return <div className="mx-auto max-w-3xl py-16 text-center"><CircleAlert className="mx-auto size-8 text-slate-400" /><h1 className="mt-4 text-xl font-semibold">Student access required</h1><p className="mt-2 text-sm text-slate-600">This workspace is available only to authenticated student accounts.</p><Button className="mt-5" onClick={() => window.location.assign("/jobs")}>Explore opportunities</Button></div>;
  }

  if (isCampusPage) {
    return <main className="mx-auto max-w-6xl space-y-6 py-2">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/jobs" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"><ArrowLeft className="size-4" /> Back to opportunities</Link>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Campus recruitment</h1>
          <p className="mt-2 text-sm text-slate-600">{selectedCampusDrive ? selectedCampusDrive.name : "Recruitment drives matched to your verified academic eligibility."}</p>
        </div>
        {selectedCampusDrive && <Button variant="outline" onClick={() => { setSelectedCampusDrive(null); setCampusOpportunities([]); setApplicationError(""); }}><ArrowLeft className="size-4" /> All eligible drives</Button>}
      </div>
      {applicationError && <div role="alert" className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><CircleAlert className="mt-0.5 size-4 shrink-0" />{applicationError}</div>}
      {applicationLoading ? <div aria-label="Loading campus recruitment" className="grid gap-3">{[1,2,3].map((n) => <div key={n} className="h-28 animate-pulse rounded-2xl border bg-slate-100" />)}</div>
        : selectedCampusDrive ? campusOpportunities.length === 0 ? <Card className="border-dashed"><CardContent className="flex flex-col items-center py-14 text-center"><BriefcaseBusiness className="size-9 text-slate-300" /><h2 className="mt-4 font-semibold text-slate-900">No eligible opportunities in this drive</h2><p className="mt-2 max-w-md text-sm leading-6 text-slate-500">The drive is eligible for your academic profile, but no currently available opportunities were returned.</p></CardContent></Card>
        : <div className="grid gap-3">{campusOpportunities.map((job) => {
          const applied = appliedIds.has(job.id);
          const expired = Boolean(job.application_deadline && new Date(job.application_deadline).getTime() < Date.now());
          return <Card key={job.id} className="border-slate-200"><CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-start">
            <CompanyMark name={job.company?.name} />
            <div className="min-w-0 flex-1"><h2 className="font-semibold text-slate-900">{job.title}</h2><p className="mt-1 text-sm text-slate-600">{job.company?.name || "Participating employer"}{job.location ? ` · ${job.location}` : ""}</p><p className="mt-3 whitespace-pre-line text-sm leading-6 text-slate-600">{job.summary || job.description || "No additional description was provided."}</p><div className="mt-3 flex flex-wrap gap-2">{job.opportunity_type && <Badge variant="secondary">{opportunityKind(job)}</Badge>}{job.work_mode && <Badge variant="outline">{job.work_mode.toLowerCase()}</Badge>}{job.application_deadline && <Badge variant="outline">Closes {dateLabel(job.application_deadline)}</Badge>}</div></div>
            <div className="sm:pt-1">{applied ? <Badge variant="secondary" className="whitespace-nowrap"><CheckCircle2 className="mr-1 size-3.5" /> Applied</Badge> : expired ? <Button disabled>Deadline passed</Button> : <Button disabled={applying === job.id} onClick={() => void apply(job)} className="whitespace-nowrap bg-teal-700 text-white hover:bg-teal-800">{applying === job.id ? "Applying…" : "Apply through Kairos"}</Button>}</div>
          </CardContent></Card>;
        })}</div>
        : campusDrives.length === 0 ? <Card className="border-dashed"><CardContent className="flex flex-col items-center py-14 text-center"><Users className="size-9 text-slate-300" /><h2 className="mt-4 font-semibold text-slate-900">No eligible campus drives</h2><p className="mt-2 max-w-md text-sm leading-6 text-slate-500">There are no active recruitment drives matching your verified academic profile right now.</p></CardContent></Card>
        : <div className="grid gap-3 md:grid-cols-2">{campusDrives.map((drive) => <Card key={drive.id} className="border-slate-200 transition hover:border-teal-300"><CardContent className="flex h-full flex-col p-5"><div className="flex items-start justify-between gap-3"><div className="flex size-11 items-center justify-center rounded-xl bg-teal-50 text-teal-800"><Building2 className="size-5" /></div><Badge variant="outline">{drive.status.replace(/_/g, " ")}</Badge></div><h2 className="mt-4 text-lg font-semibold text-slate-900">{drive.name}</h2><p className="mt-2 flex-1 text-sm leading-6 text-slate-600">{drive.description || "View eligible roles available through this campus drive."}</p><div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-500">{drive.starts_on && <span>Starts {dateLabel(drive.starts_on)}</span>}{drive.ends_on && <span>Ends {dateLabel(drive.ends_on)}</span>}</div><Button className="mt-5 bg-teal-700 text-white hover:bg-teal-800" onClick={() => { setApplicationError(""); setSelectedCampusDrive(drive); }}>View eligible opportunities <ArrowUpRight className="size-4" /></Button></CardContent></Card>)}</div>}
    </main>;
  }

  if (isApplicationsPage) {
    return <main className="mx-auto max-w-6xl space-y-6 py-2">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><Link to="/jobs" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"><ArrowLeft className="size-4" /> Back to opportunities</Link><h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">My applications</h1><p className="mt-2 text-sm text-slate-600">Keep track of the opportunities you’ve applied to and their current status.</p></div>
        <Badge variant="outline">{applications.length} records loaded</Badge>
      </div>
      {applicationError && <div role="alert" className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><CircleAlert className="mt-0.5 size-4 shrink-0" />{applicationError}</div>}
      {applicationLoading ? <div className="grid gap-3">{[1,2,3].map((n) => <div key={n} className="h-28 animate-pulse rounded-2xl border bg-slate-100" />)}</div>
        : applications.length === 0 ? <Card className="border-dashed"><CardContent className="flex flex-col items-center py-14 text-center"><BriefcaseBusiness className="size-9 text-slate-300" /><h2 className="mt-4 font-semibold text-slate-900">Your application journey starts here</h2><p className="mt-2 max-w-md text-sm leading-6 text-slate-500">When you apply to an opportunity through Kairos, its current status will appear here.</p><Button className="mt-5" onClick={() => navigate("/jobs")}>Explore opportunities</Button></CardContent></Card>
        : <div className="grid gap-3">{applications.map((app) => <Card key={app.id} className="border-slate-200"><CardContent className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center"><CompanyMark name={app.opportunity?.company?.name || app.opportunity?.company_name} /><div className="min-w-0 flex-1"><h2 className="font-semibold text-slate-900">{app.opportunity?.title || "Opportunity"}</h2><p className="mt-1 text-sm text-slate-500">{app.opportunity?.company?.name || app.opportunity?.company_name || "Employer"}{app.opportunity?.location ? ` · ${app.opportunity.location}` : ""}</p><p className="mt-2 text-xs text-slate-500">Applied · {dateLabel(app.applied_at) || "Date not supplied"}</p></div><Badge variant="outline" className="w-fit">{app.status.replace(/_/g, " ")}</Badge></CardContent></Card>)}</div>}
    </main>;
  }

  return <main className="mx-auto max-w-[1440px] space-y-7 py-2">
    <section className="relative overflow-hidden rounded-3xl border border-slate-200 bg-[linear-gradient(115deg,#f8fbfa_0%,#ffffff_58%,#f3f8f7_100%)] px-5 py-8 sm:px-8 sm:py-10">
      <div className="relative max-w-3xl">
        <div className="inline-flex items-center gap-2 rounded-full border border-teal-800/10 bg-white/80 px-3 py-1.5 text-xs font-medium text-teal-800"><Sparkles className="size-3.5" /> Your next chapter starts here</div>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">Find your next opportunity</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">Discover internships, graduate roles, and opportunities that move your career forward.</p>
        <form onSubmit={runSearch} className="mt-6 grid gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_auto]">
          <label className="flex min-w-0 items-center gap-2 px-3"><Search className="size-4 shrink-0 text-slate-400" /><span className="sr-only">Search title, skill, or company</span><Input aria-label="Search title, skill, or company" className="h-10 border-0 px-0 shadow-none focus-visible:ring-0" placeholder="Job title, keyword, or company" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
          <label className="flex min-w-0 items-center gap-2 border-slate-100 px-3 md:border-l"><MapPin className="size-4 shrink-0 text-slate-400" /><span className="sr-only">Location</span><Input aria-label="Location" className="h-10 border-0 px-0 shadow-none focus-visible:ring-0" placeholder="City or remote" value={location} onChange={(event) => setLocation(event.target.value)} /></label>
          <Button type="submit" className="h-10 bg-teal-700 px-5 text-white hover:bg-teal-800"><Search className="size-4" /> Search jobs</Button>
        </form>
      </div>
    </section>

    <nav aria-label="Jobs navigation" className="flex flex-wrap gap-2 border-b border-slate-200 pb-4">
      <Button variant="secondary" className="rounded-full"><Search className="size-4" /> Explore opportunities</Button>
      {!account && <Button variant="outline" className="rounded-full" onClick={() => window.location.assign("/auth/auth2/login")}>Sign in</Button>}
      {isStudent && <Button variant="ghost" className="rounded-full" onClick={() => navigate("/jobs/applications")}><CheckCircle2 className="size-4" /> My applications</Button>}
      {isStudent && <Button variant="ghost" className="rounded-full" onClick={() => navigate("/jobs/campus")}><Users className="size-4" /> Campus recruitment</Button>}
    </nav>

    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.04fr)_minmax(400px,0.96fr)]">
      <section className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-lg font-semibold text-slate-950">Explore opportunities</h2><p className="mt-1 text-sm text-slate-500">{loading ? "Finding opportunities…" : `${result.items.length ? `${result.offset + 1}–${result.offset + result.items.length}` : "0"} shown · results from Kairos`}</p></div><Button variant="ghost" size="sm" onClick={() => void loadJobs()} disabled={loading}><RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} /> Refresh</Button></div>

        <div className="rounded-2xl border border-slate-200 bg-white p-3">
          <div className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-700"><SlidersHorizontal className="size-4" /> Refine your search</div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1.5 text-xs font-medium text-slate-600">Opportunity type<select aria-label="Opportunity type" className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm font-normal text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30" value={kind} onChange={(event) => { setKind(event.target.value); setOffset(0); }} >{TYPES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
            <label className="space-y-1.5 text-xs font-medium text-slate-600">Workplace<select aria-label="Workplace arrangement" className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm font-normal text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30" value={mode} onChange={(event) => { setMode(event.target.value); setOffset(0); }} >{MODES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          </div>
          {(query || location || kind || mode) && <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3"><span className="text-xs text-slate-500">Active filters</span>{query && <Badge variant="secondary">Keyword: {query}<button aria-label="Remove keyword filter" className="ml-1" onClick={() => setQuery("")}><X className="size-3" /></button></Badge>}{location && <Badge variant="secondary">Location: {location}<button aria-label="Remove location filter" className="ml-1" onClick={() => setLocation("")}><X className="size-3" /></button></Badge>}{kind && <Badge variant="secondary">{TYPES.find((item) => item.value === kind)?.label}<button aria-label="Remove type filter" className="ml-1" onClick={() => setKind("")}><X className="size-3" /></button></Badge>}{mode && <Badge variant="secondary">{MODES.find((item) => item.value === mode)?.label}<button aria-label="Remove workplace filter" className="ml-1" onClick={() => setMode("")}><X className="size-3" /></button></Badge>}<Button variant="link" size="sm" onClick={clearFilters}>Clear all</Button></div>}
        </div>

        {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><div className="flex items-start gap-2"><CircleAlert className="mt-0.5 size-4 shrink-0" /><div className="flex-1">{error}<div className="mt-3"><Button size="sm" variant="outline" onClick={() => void loadJobs()}>Try again</Button></div></div></div></div>}
        {applicationError && <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{applicationError}<button className="ml-2 underline" onClick={() => setApplicationError("")}>Dismiss</button></div>}
        {loading ? <div aria-label="Loading opportunities" className="space-y-3">{[1,2,3].map((n) => <div key={n} className="h-48 animate-pulse rounded-2xl border border-slate-200 bg-slate-100" />)}</div>
          : !error && result.items.length === 0 ? <Card className="border-dashed"><CardContent className="flex flex-col items-center py-12 text-center"><BriefcaseBusiness className="size-9 text-slate-300" /><h3 className="mt-4 font-semibold text-slate-900">No opportunities found</h3><p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">Try a different keyword or clear some filters to see more opportunities.</p><Button variant="outline" className="mt-4" onClick={clearFilters}>Clear filters</Button></CardContent></Card>
          : result.items.map((job) => <OpportunityCard key={job.id} job={job} selected={job.id === selectedId} onSelect={() => { setSelectedId(job.id); if (window.matchMedia("(max-width: 1279px)").matches) navigate(`/jobs/${encodeURIComponent(job.id)}`); }} />)}
        <div className="flex items-center justify-between border-t border-slate-200 pt-4">
          <span className="text-xs text-slate-500">Page size {PAGE_SIZE}</span>
          <div className="flex gap-2"><Button variant="outline" size="sm" disabled={offset <= 0 || loading} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}><ChevronLeft className="size-4" /> Previous</Button><Button variant="outline" size="sm" disabled={loading || result.items.length < PAGE_SIZE} onClick={() => setOffset(offset + PAGE_SIZE)}>Next <ChevronRight className="size-4" /></Button></div>
        </div>
      </section>

      <aside className="hidden min-w-0 xl:block">
        <div className="sticky top-4 space-y-3">
          {selected && !error ? <DetailPanel job={selected} account={account} appliedIds={appliedIds} onApply={apply} applying={applying} />
            : <div className="flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center"><BriefcaseBusiness className="size-8 text-slate-300" /><p className="mt-3 font-medium text-slate-800">Select an opportunity</p><p className="mt-1 text-sm text-slate-500">Role details and application options will appear here.</p></div>}
          <p className="px-1 text-xs leading-5 text-slate-500">Public listings are sourced from Kairos. Campus-linked opportunities are kept in the eligible campus recruitment workflow.</p>
        </div>
      </aside>
    </div>
  </main>;
}

export function JobDetailRoute() {
  const { jobId = "" } = useParams();
  const { account } = useAuth();
  const [job, setJob] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());
  const [applying, setApplying] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setJob(null);
    apiRequest<Opportunity>(`/jobs/${encodeURIComponent(jobId)}`, { signal: controller.signal })
      .then(setJob).catch((err) => { if (!controller.signal.aborted) setError(errorMessage(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [jobId]);
  useEffect(() => {
    if (!account?.roles?.some((role) => role.toUpperCase() === "STUDENT")) return;
    const controller = new AbortController();
    apiRequest<{ items: Application[] }>("/modules/internships/applications/me", { signal: controller.signal })
      .then((data) => setAppliedIds(new Set((data.items || []).map((item) => item.opportunity_id || item.opportunity?.id).filter((id): id is string => Boolean(id)))))
      .catch(() => { /* Keep the detail page available if history cannot be loaded. */ });
    return () => controller.abort();
  }, [account]);
  const apply = async (item: Opportunity) => {
    setApplying(item.id); setActionError("");
    try { await apiRequest(`/modules/internships/opportunities/${encodeURIComponent(item.id)}/applications`, { method: "POST" }); setAppliedIds((prev) => new Set(prev).add(item.id)); }
    catch (err) { setActionError(errorMessage(err)); } finally { setApplying(null); }
  };
  return <main className="mx-auto max-w-4xl space-y-4 py-2"><Link to="/jobs" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"><ArrowLeft className="size-4" /> Back to opportunities</Link>{loading ? <div className="h-96 animate-pulse rounded-2xl bg-slate-100" /> : error ? <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-800">{error}<div className="mt-3"><Button variant="outline" onClick={() => window.location.assign("/jobs")}>Return to search</Button></div></div> : job ? <><h1 className="sr-only">{job.title}</h1>{actionError && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{actionError}</div>}<DetailPanel job={job} account={account} appliedIds={appliedIds} onApply={apply} applying={applying} /></> : null}</main>;
}
