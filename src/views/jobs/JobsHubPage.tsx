import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams, useParams } from "react-router";
import {
  ArrowLeft, ArrowUpRight, Bookmark, BriefcaseBusiness, Building2, CalendarDays,
  CheckCircle2, ChevronLeft, ChevronRight, CircleAlert, ExternalLink,
  MapPin, RefreshCw, Search, SlidersHorizontal, Users, X,
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
type PageResult = { items: Opportunity[]; limit: number; offset: number; hasMore?: boolean };
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
  { label: "Jobs", value: "JOB" },
];
const MODES = [
  { label: "Any workplace", value: "" },
  { label: "On-site", value: "ONSITE" },
  { label: "Hybrid", value: "HYBRID" },
  { label: "Remote", value: "REMOTE" },
];
const EMPLOYMENT_TYPES = [
  { label: "Any employment type", value: "" },
  { label: "Full-time", value: "FULL_TIME" },
  { label: "Part-time", value: "PART_TIME" },
  { label: "Internship", value: "INTERNSHIP" },
  { label: "Contract", value: "CONTRACT" },
  { label: "Temporary", value: "TEMPORARY" },
];
const POSTED_WINDOWS = [
  { label: "Any time", value: "" },
  { label: "Past 24 hours", value: "1" },
  { label: "Past 7 days", value: "7" },
  { label: "Past 30 days", value: "30" },
];

function dateLabel(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
function isDeadlinePassed(value?: string | null) {
  if (!value) return false;
  const deadline = value.slice(0, 10);
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  return deadline < today;
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
  return <div aria-hidden="true" className="flex size-12 shrink-0 items-center justify-center rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-sm font-semibold tracking-wide text-slate-700 dark:text-slate-300">{companyInitials(name)}</div>;
}

function OpportunityCard({ job, selected, saved, onSelect, onToggleSave }: { job: Opportunity; selected: boolean; saved: boolean; onSelect: () => void; onToggleSave: (job: Opportunity) => void }) {
  const company = job.company?.name || "Employer";
  const salary = salaryLabel(job);
  return (
    <article className={`group rounded-xl border bg-white dark:bg-slate-950 p-4 transition-colors hover:border-teal-300 focus-within:ring-2 focus-within:ring-teal-700/20 sm:p-5 ${selected ? "border-teal-600 ring-1 ring-teal-600/10" : "border-slate-200 dark:border-slate-800"}`}>
      <div className="flex items-start gap-3 sm:gap-4">
        <CompanyMark name={company} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <Link to={`/jobs/${encodeURIComponent(job.id)}`} className="inline-block text-left text-base font-semibold leading-6 text-slate-900 dark:text-slate-100 underline-offset-4 hover:text-teal-800 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-700">
                {job.title}
              </Link>
              <p className="mt-0.5 truncate text-sm text-slate-600 dark:text-slate-400">{company}</p>
            </div>
            <Badge variant="outline" className="shrink-0 border-slate-200 dark:border-slate-800 font-medium capitalize text-slate-600 dark:text-slate-400">{opportunityKind(job)}</Badge>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-slate-500 dark:text-slate-400">
            {job.location && <span className="inline-flex items-center gap-1"><MapPin className="size-3.5" />{job.location}</span>}
            {job.work_mode && <span className="inline-flex items-center gap-1"><Building2 className="size-3.5" />{job.work_mode.toLowerCase()}</span>}
            {salary && <span className="font-medium text-slate-700 dark:text-slate-300">{salary}</span>}
          </div>
          <p className="mt-3 line-clamp-2 text-sm leading-5 text-slate-600 dark:text-slate-400">{job.summary || job.description || "Open the opportunity to review the full role details and application instructions."}</p>
          <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-2">
            {(job.required_skills || []).slice(0, 3).map((skill) => <Badge key={skill} variant="secondary" className="rounded-md font-normal text-slate-600 dark:text-slate-400">{skill}</Badge>)}
            {job.application_deadline && <span className="inline-flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400"><CalendarDays className="size-3.5" />Closes {dateLabel(job.application_deadline)}</span>}
            {job.created_at && <span className="text-xs text-slate-500 dark:text-slate-400">Posted {dateLabel(job.created_at)}</span>}
            <div className="ml-auto flex items-center gap-1"><Button type="button" variant="ghost" size="icon" className="size-8" aria-label={saved ? `Remove ${job.title} from saved jobs` : `Save ${job.title}`} aria-pressed={saved} onClick={() => onToggleSave(job)}><Bookmark className={`size-4 ${saved ? "fill-current text-primary" : ""}`} /></Button><Button variant="ghost" size="sm" className="h-8 text-primary hover:bg-accent" onClick={onSelect}>View details <ArrowUpRight className="size-3.5" /></Button></div>
          </div>
        </div>
      </div>
    </article>
  );
}

function DetailPanel({ job, account, appliedIds, saved, onApply, onToggleSave, applying }: {
  job: Opportunity; account: KairosAccount | null; appliedIds: Set<string>; saved: boolean;
  onApply: (job: Opportunity) => void; onToggleSave: (job: Opportunity) => void; applying: string | null;
}) {
  const company = job.company?.name || "Employer";
  const applied = appliedIds.has(job.id);
  const expired = isDeadlinePassed(job.application_deadline);
  const externalUrl = job.public_application_url;
  const canApply = account?.roles?.some((role) => role.toUpperCase() === "STUDENT");
  const validExternal = (() => {
    if (!externalUrl) return false;
    try { const parsed = new URL(externalUrl); return parsed.protocol === "https:" || parsed.protocol === "http:"; }
    catch { return false; }
  })();
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
      <div className="border-b border-slate-100 dark:border-slate-800 p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <CompanyMark name={company} />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-slate-600 dark:text-slate-400">{company}</p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-950 dark:text-slate-100">{job.title}</h2>
            <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500 dark:text-slate-400">
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
        <div className="mt-4 flex flex-wrap gap-2"><Button type="button" variant="outline" size="sm" aria-pressed={saved} onClick={() => onToggleSave(job)}><Bookmark className={`size-4 ${saved ? "fill-current" : ""}`} />{saved ? "Saved" : "Save job"}</Button></div>
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
        {validExternal && canApply && <p className="mt-3 flex items-start gap-1.5 text-xs leading-5 text-slate-500 dark:text-slate-400"><ExternalLink className="mt-0.5 size-3.5 shrink-0" />You’ll leave Kairos to complete your application on the company website.</p>}
        {!validExternal && job.public_application_url && <p role="status" className="mt-3 text-xs text-amber-700">The stored external link is invalid. You can still apply through Kairos if eligible.</p>}
        {canApply && !externalUrl && !applied && !expired && <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">Your application will be submitted to Kairos using the existing student application workflow.</p>}
      </div>
      <div className="space-y-6 p-5 sm:p-6">
        <section><h3 className="font-semibold text-slate-900 dark:text-slate-100">About the role</h3><p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-600 dark:text-slate-400">{job.description || job.summary || "The employer has not supplied a full description."}</p></section>
        {job.required_skills?.length ? <section><h3 className="font-semibold text-slate-900 dark:text-slate-100">Required skills</h3><div className="mt-2 flex flex-wrap gap-2">{job.required_skills.map((skill) => <Badge variant="secondary" key={skill}>{skill}</Badge>)}</div></section> : null}
        {job.preferred_skills?.length ? <section><h3 className="font-semibold text-slate-900 dark:text-slate-100">Preferred skills</h3><div className="mt-2 flex flex-wrap gap-2">{job.preferred_skills.map((skill) => <Badge variant="outline" key={skill}>{skill}</Badge>)}</div></section> : null}
        {job.education_requirements && <section><h3 className="font-semibold text-slate-900 dark:text-slate-100">Education requirements</h3><p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-400">{job.education_requirements}</p></section>}
        <section className="grid gap-4 border-t border-slate-100 dark:border-slate-800 pt-5 sm:grid-cols-2">
          {job.application_deadline && <div><p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Application deadline</p><p className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-200">{dateLabel(job.application_deadline)}</p></div>}
          {(job.experience_min_years != null || job.experience_max_years != null) && <div><p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Experience</p><p className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-200">{job.experience_min_years ?? 0}{job.experience_max_years != null ? `–${job.experience_max_years}` : "+"} years</p></div>}
          {job.department && <div><p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Team</p><p className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-200">{job.department}</p></div>}
          {job.starts_on && <div><p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Expected start</p><p className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-200">{dateLabel(job.starts_on)}</p></div>}
        </section>
      </div>
    </div>
  );
}

export default function JobsHubPage() {
  const { account } = useAuth();
  const routeLocation = useLocation();
  const [params, setParams] = useSearchParams();
  const initialJobId = useRef(params.get("job") || "");
  const [deepLinkedJob, setDeepLinkedJob] = useState<Opportunity | null>(null);
  const [deepLinkError, setDeepLinkError] = useState("");
  const [query, setQuery] = useState(params.get("q") || "");
  const [queryInput, setQueryInput] = useState(params.get("q") || "");
  const [location, setLocation] = useState(params.get("location") || "");
  const [locationInput, setLocationInput] = useState(params.get("location") || "");
  const [kind, setKind] = useState(params.get("opportunity_type") || "");
  const [mode, setMode] = useState(params.get("work_mode") || "");
  const [employmentType, setEmploymentType] = useState(params.get("employment_type") || "");
  const [sortBy, setSortBy] = useState(params.get("sort_by") || "newest");
  const [postedWithinDays, setPostedWithinDays] = useState(params.get("posted_within_days") || "");
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
  const [savedJobs, setSavedJobs] = useState<Opportunity[]>([]);
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [savedLoading, setSavedLoading] = useState(false);
  const [campusDrives, setCampusDrives] = useState<CampusDrive[]>([]);
  const [selectedCampusDrive, setSelectedCampusDrive] = useState<CampusDrive | null>(null);
  const [campusOpportunities, setCampusOpportunities] = useState<CampusOpportunity[]>([]);
  const navigate = useNavigate();
  const isStudent = Boolean(account?.roles?.some((role) => role.toUpperCase() === "STUDENT"));
  const isApplicationsPage = routeLocation.pathname === "/jobs/applications";
  const isCampusPage = routeLocation.pathname === "/jobs/campus";
  const isSavedPage = routeLocation.pathname === "/jobs/saved";

  const loadJobs = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    const search = new URLSearchParams();
    if (query.trim()) search.set("q", query.trim());
    if (location.trim()) search.set("location", location.trim());
    if (kind) search.set("opportunity_type", kind);
    if (mode) search.set("work_mode", mode);
    if (employmentType) search.set("employment_type", employmentType);
    if (sortBy) search.set("sort_by", sortBy);
    if (postedWithinDays) search.set("posted_within_days", postedWithinDays);
    search.set("limit", String(PAGE_SIZE + 1));
    search.set("offset", String(offset));
    try {
      const data = await apiRequest<PageResult>(`/jobs?${search.toString()}`, { signal });
      const visibleItems = data.items.slice(0, PAGE_SIZE);
      setResult({ ...data, items: visibleItems, hasMore: data.items.length > PAGE_SIZE });
      setSelectedId((current) => {
        if (current && visibleItems.some((item) => item.id === current)) return current;
        if (current && current === initialJobId.current) return current;
        return visibleItems[0]?.id || "";
      });
    } catch (err) {
      if (signal?.aborted) return;
      setError(errorMessage(err));
      setResult({ items: [], limit: PAGE_SIZE, offset });
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [query, location, kind, mode, employmentType, sortBy, postedWithinDays, offset]);

  useEffect(() => {
    if (isApplicationsPage || isCampusPage || isSavedPage) return;
    const controller = new AbortController();
    void loadJobs(controller.signal);
    return () => controller.abort();
  }, [loadJobs, isApplicationsPage, isCampusPage, isSavedPage]);

  useEffect(() => {
    const next = new URLSearchParams();
    if (query.trim()) next.set("q", query.trim());
    if (location.trim()) next.set("location", location.trim());
    if (kind) next.set("opportunity_type", kind);
    if (mode) next.set("work_mode", mode);
    if (employmentType) next.set("employment_type", employmentType);
    if (sortBy !== "newest") next.set("sort_by", sortBy);
    if (postedWithinDays) next.set("posted_within_days", postedWithinDays);
    if (offset) next.set("offset", String(offset));
    if (selectedId) next.set("job", selectedId);
    if (next.toString() !== params.toString()) setParams(next, { replace: true });
  }, [query, location, kind, mode, employmentType, sortBy, postedWithinDays, offset, selectedId, params, setParams]);

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

  useEffect(() => {
    if (!isStudent) {
      setSavedJobs([]);
      setSavedIds(new Set());
      return;
    }
    const controller = new AbortController();
    setSavedLoading(true);
    apiRequest<{ items: Opportunity[] }>("/students/saved-jobs", { signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        const items = data.items || [];
        setSavedJobs(items);
        setSavedIds(new Set(items.map((item) => item.id)));
      })
      .catch((err) => {
        if (!controller.signal.aborted && isSavedPage) setApplicationError(errorMessage(err));
      })
      .finally(() => { if (!controller.signal.aborted) setSavedLoading(false); });
    return () => controller.abort();
  }, [isStudent, isSavedPage]);

  const toggleSavedJob = async (job: Opportunity) => {
    if (!account) {
      navigate("/auth/auth2/login");
      return;
    }
    if (!isStudent) {
      setApplicationError("Saved jobs are available to student accounts.");
      return;
    }
    const wasSaved = savedIds.has(job.id);
    setApplicationError("");
    try {
      await apiRequest(`/students/saved-jobs/${encodeURIComponent(job.id)}`, { method: wasSaved ? "DELETE" : "POST" });
      setSavedIds((current) => {
        const next = new Set(current);
        if (wasSaved) next.delete(job.id); else next.add(job.id);
        return next;
      });
      setSavedJobs((current) => wasSaved ? current.filter((item) => item.id !== job.id) : [job, ...current.filter((item) => item.id !== job.id)]);
    } catch (err) {
      setApplicationError(errorMessage(err));
    }
  };

  useEffect(() => {
    const requestedId = params.get("job");
    if (!requestedId || result.items.some((item) => item.id === requestedId)) {
      setDeepLinkedJob(null);
      setDeepLinkError("");
      return;
    }
    const controller = new AbortController();
    setDeepLinkError("");
    apiRequest<Opportunity>(`/jobs/${encodeURIComponent(requestedId)}`, { signal: controller.signal })
      .then((job) => {
        if (controller.signal.aborted) return;
        setDeepLinkedJob(job);
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setDeepLinkedJob(null);
          setDeepLinkError(errorMessage(err));
        }
      });
    return () => controller.abort();
  }, [params, result.items]);

  const selected = useMemo(
    () => result.items.find((job) => job.id === selectedId) || (deepLinkedJob?.id === selectedId ? deepLinkedJob : null),
    [result.items, selectedId, deepLinkedJob],
  );

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

  const clearFilters = () => { setQuery(""); setQueryInput(""); setLocation(""); setLocationInput(""); setKind(""); setMode(""); setEmploymentType(""); setSortBy("newest"); setPostedWithinDays(""); setOffset(0); };
  const runSearch = (event: FormEvent) => {
    event.preventDefault();
    const nextQuery = queryInput.trim();
    const nextLocation = locationInput.trim();
    const unchanged = nextQuery === query && nextLocation === location && offset === 0;
    setQuery(nextQuery);
    setLocation(nextLocation);
    setOffset(0);
    if (unchanged) void loadJobs();
  };

  if ((isApplicationsPage || isCampusPage || isSavedPage) && !isStudent) {
    return <div className="mx-auto max-w-3xl py-16 text-center"><CircleAlert className="mx-auto size-8 text-slate-400 dark:text-slate-500" /><h1 className="mt-4 text-xl font-semibold">Student access required</h1><p className="mt-2 text-sm text-slate-600 dark:text-slate-400">This workspace is available only to authenticated student accounts.</p><Button className="mt-5" onClick={() => window.location.assign("/jobs")}>Explore opportunities</Button></div>;
  }

  if (isSavedPage) {
    return <main className="mx-auto max-w-5xl space-y-5 py-2">
      <div><Link to="/jobs" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="size-4" /> Back to opportunities</Link><h1 className="mt-3 text-3xl font-semibold tracking-tight">Saved jobs</h1><p className="mt-2 text-sm text-muted-foreground">Your saved Kairos opportunities, available across sessions.</p></div>
      {applicationError && <div role="alert" className="rounded-xl border border-destructive/25 bg-destructive/5 p-4 text-sm text-destructive">{applicationError}<Button variant="link" size="sm" onClick={() => { setApplicationError(""); setSavedLoading(true); apiRequest<{items: Opportunity[]}>("/students/saved-jobs").then(data => { setSavedJobs(data.items || []); setSavedIds(new Set((data.items || []).map(item => item.id))); }).catch(err => setApplicationError(errorMessage(err))).finally(() => setSavedLoading(false)); }}>Retry</Button></div>}
      {savedLoading ? <div aria-label="Loading saved jobs" className="space-y-3">{[1,2,3].map(n => <div key={n} className="h-32 animate-pulse rounded-xl border border-border bg-muted/50" />)}</div>
        : savedJobs.length === 0 ? <Card className="border-dashed"><CardContent className="flex flex-col items-center py-14 text-center"><Bookmark className="size-8 text-muted-foreground" /><h2 className="mt-4 font-semibold">No saved jobs yet</h2><p className="mt-2 max-w-md text-sm text-muted-foreground">Save a promising role from discovery and it will be waiting here when you return.</p><Button className="mt-5" onClick={() => navigate("/jobs")}>Explore jobs</Button></CardContent></Card>
        : <div className="space-y-3">{savedJobs.map(job => <OpportunityCard key={job.id} job={job} selected={job.id === selectedId} saved={true} onSelect={() => navigate(`/jobs/${encodeURIComponent(job.id)}`)} onToggleSave={toggleSavedJob} />)}</div>}
    </main>;
  }

  if (isCampusPage) {
    return <main className="mx-auto max-w-6xl space-y-6 py-2">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/jobs" className="inline-flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:text-slate-100"><ArrowLeft className="size-4" /> Back to opportunities</Link>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 dark:text-slate-100">Campus recruitment</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{selectedCampusDrive ? selectedCampusDrive.name : "Recruitment drives matched to your verified academic eligibility."}</p>
        </div>
        {selectedCampusDrive && <Button variant="outline" onClick={() => { setSelectedCampusDrive(null); setCampusOpportunities([]); setApplicationError(""); }}><ArrowLeft className="size-4" /> All eligible drives</Button>}
      </div>
      {applicationError && <div role="alert" className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><CircleAlert className="mt-0.5 size-4 shrink-0" />{applicationError}</div>}
      {applicationLoading ? <div aria-label="Loading campus recruitment" className="grid gap-3">{[1,2,3].map((n) => <div key={n} className="h-28 animate-pulse rounded-2xl border bg-slate-100 dark:bg-slate-900" />)}</div>
        : selectedCampusDrive ? campusOpportunities.length === 0 ? <Card className="border-dashed"><CardContent className="flex flex-col items-center py-14 text-center"><BriefcaseBusiness className="size-9 text-slate-300 dark:text-slate-600" /><h2 className="mt-4 font-semibold text-slate-900 dark:text-slate-100">No eligible opportunities in this drive</h2><p className="mt-2 max-w-md text-sm leading-6 text-slate-500 dark:text-slate-400">The drive is eligible for your academic profile, but no currently available opportunities were returned.</p></CardContent></Card>
        : <div className="grid gap-3">{campusOpportunities.map((job) => {
          const applied = appliedIds.has(job.id);
          const expired = isDeadlinePassed(job.application_deadline);
          return <Card key={job.id} className="border-slate-200 dark:border-slate-800"><CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-start">
            <CompanyMark name={job.company?.name} />
            <div className="min-w-0 flex-1"><h2 className="font-semibold text-slate-900 dark:text-slate-100">{job.title}</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{job.company?.name || "Participating employer"}{job.location ? ` · ${job.location}` : ""}</p><p className="mt-3 whitespace-pre-line text-sm leading-6 text-slate-600 dark:text-slate-400">{job.summary || job.description || "No additional description was provided."}</p><div className="mt-3 flex flex-wrap gap-2">{job.opportunity_type && <Badge variant="secondary">{opportunityKind(job)}</Badge>}{job.work_mode && <Badge variant="outline">{job.work_mode.toLowerCase()}</Badge>}{job.application_deadline && <Badge variant="outline">Closes {dateLabel(job.application_deadline)}</Badge>}</div></div>
            <div className="sm:pt-1">{applied ? <Badge variant="secondary" className="whitespace-nowrap"><CheckCircle2 className="mr-1 size-3.5" /> Applied</Badge> : expired ? <Button disabled>Deadline passed</Button> : <Button disabled={applying === job.id} onClick={() => void apply(job)} className="whitespace-nowrap bg-teal-700 text-white hover:bg-teal-800">{applying === job.id ? "Applying…" : "Apply through Kairos"}</Button>}</div>
          </CardContent></Card>;
        })}</div>
        : campusDrives.length === 0 ? <Card className="border-dashed"><CardContent className="flex flex-col items-center py-14 text-center"><Users className="size-9 text-slate-300 dark:text-slate-600" /><h2 className="mt-4 font-semibold text-slate-900 dark:text-slate-100">No eligible campus drives</h2><p className="mt-2 max-w-md text-sm leading-6 text-slate-500 dark:text-slate-400">There are no active recruitment drives matching your verified academic profile right now.</p></CardContent></Card>
        : <div className="grid gap-3 md:grid-cols-2">{campusDrives.map((drive) => <Card key={drive.id} className="border-slate-200 dark:border-slate-800 transition hover:border-teal-300"><CardContent className="flex h-full flex-col p-5"><div className="flex items-start justify-between gap-3"><div className="flex size-11 items-center justify-center rounded-xl bg-teal-50 text-teal-800"><Building2 className="size-5" /></div><Badge variant="outline">{drive.status.replace(/_/g, " ")}</Badge></div><h2 className="mt-4 text-lg font-semibold text-slate-900 dark:text-slate-100">{drive.name}</h2><p className="mt-2 flex-1 text-sm leading-6 text-slate-600 dark:text-slate-400">{drive.description || "View eligible roles available through this campus drive."}</p><div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-500 dark:text-slate-400">{drive.starts_on && <span>Starts {dateLabel(drive.starts_on)}</span>}{drive.ends_on && <span>Ends {dateLabel(drive.ends_on)}</span>}</div><Button className="mt-5 bg-teal-700 text-white hover:bg-teal-800" onClick={() => { setApplicationError(""); setSelectedCampusDrive(drive); }}>View eligible opportunities <ArrowUpRight className="size-4" /></Button></CardContent></Card>)}</div>}
    </main>;
  }

  if (isApplicationsPage) {
    return <main className="mx-auto max-w-6xl space-y-6 py-2">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><Link to="/jobs" className="inline-flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:text-slate-100"><ArrowLeft className="size-4" /> Back to opportunities</Link><h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 dark:text-slate-100">My applications</h1><p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Keep track of the opportunities you’ve applied to and their current status.</p></div>
        <Badge variant="outline">{applications.length} records loaded</Badge>
      </div>
      {applicationError && <div role="alert" className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><CircleAlert className="mt-0.5 size-4 shrink-0" />{applicationError}</div>}
      {applicationLoading ? <div className="grid gap-3">{[1,2,3].map((n) => <div key={n} className="h-28 animate-pulse rounded-2xl border bg-slate-100 dark:bg-slate-900" />)}</div>
        : applications.length === 0 ? <Card className="border-dashed"><CardContent className="flex flex-col items-center py-14 text-center"><BriefcaseBusiness className="size-9 text-slate-300 dark:text-slate-600" /><h2 className="mt-4 font-semibold text-slate-900 dark:text-slate-100">Your application journey starts here</h2><p className="mt-2 max-w-md text-sm leading-6 text-slate-500 dark:text-slate-400">When you apply to an opportunity through Kairos, its current status will appear here.</p><Button className="mt-5" onClick={() => navigate("/jobs")}>Explore opportunities</Button></CardContent></Card>
        : <div className="grid gap-3">{applications.map((app) => <Card key={app.id} className="border-slate-200 dark:border-slate-800"><CardContent className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center"><CompanyMark name={app.opportunity?.company?.name || app.opportunity?.company_name} /><div className="min-w-0 flex-1"><h2 className="font-semibold text-slate-900 dark:text-slate-100">{app.opportunity?.title || "Opportunity"}</h2><p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{app.opportunity?.company?.name || app.opportunity?.company_name || "Employer"}{app.opportunity?.location ? ` · ${app.opportunity.location}` : ""}</p><p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Applied · {dateLabel(app.applied_at) || "Date not supplied"}</p></div><Badge variant="outline" className="w-fit">{app.status.replace(/_/g, " ")}</Badge></CardContent></Card>)}</div>}
    </main>;
  }

  return <main className="mx-auto max-w-[1440px] space-y-5 py-1">
    <section className="space-y-1 border-b border-slate-200 dark:border-slate-800 pb-5">
      <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-slate-100 sm:text-[28px]">Find your next opportunity</h1>
      <p className="text-sm leading-6 text-muted-foreground">Explore internships, graduate roles, and jobs that fit your goals.</p>
      <form onSubmit={runSearch} className="mt-4 grid gap-2 rounded-xl border border-border bg-card p-2 shadow-sm sm:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)_auto]">
        <label className="flex min-w-0 items-center gap-2 px-2"><Search className="size-4 shrink-0 text-slate-400 dark:text-slate-500" /><span className="sr-only">Search title, skill, or company</span><Input aria-label="Search title, skill, or company" className="h-9 border-0 px-0 shadow-none focus-visible:ring-0" placeholder="Role, skill, or company" value={queryInput} onChange={(event) => setQueryInput(event.target.value)} /></label>
        <label className="flex min-w-0 items-center gap-2 px-2 sm:border-l sm:border-slate-200 dark:border-slate-800"><MapPin className="size-4 shrink-0 text-slate-400 dark:text-slate-500" /><span className="sr-only">Location</span><Input aria-label="Location" className="h-9 border-0 px-0 shadow-none focus-visible:ring-0" placeholder="City or remote" value={locationInput} onChange={(event) => setLocationInput(event.target.value)} /></label>
        <div className="flex gap-1">
          {(queryInput || locationInput) && <Button type="button" variant="ghost" className="h-9 px-3" aria-label="Clear search fields" onClick={() => { setQueryInput(""); setLocationInput(""); setQuery(""); setLocation(""); setOffset(0); }}><X className="size-4" /><span className="sm:hidden">Clear</span></Button>}
          <Button type="submit" className="h-9 bg-teal-700 px-5 text-white hover:bg-teal-800"><Search className="size-4" /> Search</Button>
        </div>
      </form>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">Kairos listings are managed here. External discovery opens HiringCafe directly.</p>
        <a href="https://hiringcafe.com/" target="_blank" rel="noopener noreferrer" className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-border bg-background px-3 text-sm font-medium transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><ExternalLink className="size-4" /> Explore HiringCafe <span className="sr-only">(opens in a new tab)</span></a>
      </div>
    </section>

    <nav aria-label="Jobs navigation" className="flex flex-wrap items-center gap-1 border-b border-slate-200 dark:border-slate-800 pb-3">
      <Button variant="secondary" className="rounded-full"><Search className="size-4" /> Explore opportunities</Button>
      {account && <Button variant="ghost" className="rounded-full" onClick={() => navigate("/")}>Back to workspace</Button>}
      {!account && <Button variant="outline" className="rounded-full" onClick={() => window.location.assign("/auth/auth2/login")}>Sign in</Button>}
      {isStudent && <Button variant="ghost" className="rounded-full" onClick={() => navigate("/jobs/saved")}><Bookmark className="size-4" /> Saved jobs{savedIds.size ? ` · ${savedIds.size}` : ""}</Button>}
      {isStudent && <Button variant="ghost" className="rounded-full" onClick={() => navigate("/jobs/applications")}><CheckCircle2 className="size-4" /> My applications</Button>
      {isStudent && <Button variant="ghost" className="rounded-full" onClick={() => navigate("/jobs/campus")}><Users className="size-4" /> Campus recruitment</Button>}
    </nav>

    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
      <section className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-base font-semibold text-slate-950 dark:text-slate-100">Open opportunities</h2><p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{loading ? "Loading results…" : `${result.items.length ? `${result.offset + 1}–${result.offset + result.items.length}` : "0"} shown · ${result.hasMore ? "more available" : "end of results"}`}</p></div><Button variant="ghost" size="sm" onClick={() => void loadJobs()} disabled={loading}><RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} /> Refresh</Button></div>

        <div className="border-y border-slate-200 dark:border-slate-800 py-3">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"><SlidersHorizontal className="size-3.5" /> Filters</div>
          <div className="flex flex-wrap items-end gap-3">
            <label className="min-w-40 space-y-1.5 text-xs font-medium text-slate-600 dark:text-slate-400">Opportunity type<select aria-label="Opportunity type" className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm font-normal text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30" value={kind} onChange={(event) => { setKind(event.target.value); setOffset(0); }} >{TYPES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
            <label className="min-w-40 space-y-1.5 text-xs font-medium text-slate-600 dark:text-slate-400">Workplace<select aria-label="Workplace arrangement" className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm font-normal text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30" value={mode} onChange={(event) => { setMode(event.target.value); setOffset(0); }} >{MODES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
            <label className="min-w-40 space-y-1.5 text-xs font-medium text-slate-600 dark:text-slate-400">Employment type<select aria-label="Employment type" className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm font-normal text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30" value={employmentType} onChange={(event) => { setEmploymentType(event.target.value); setOffset(0); }} >{EMPLOYMENT_TYPES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
            <label className="min-w-36 space-y-1.5 text-xs font-medium text-slate-600 dark:text-slate-400">Posted<select aria-label="Posted within" className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm font-normal text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30" value={postedWithinDays} onChange={(event) => { setPostedWithinDays(event.target.value); setOffset(0); }} >{POSTED_WINDOWS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
            <label className="min-w-36 space-y-1.5 text-xs font-medium text-slate-600 dark:text-slate-400">Sort by<select aria-label="Sort jobs" className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm font-normal text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30" value={sortBy} onChange={(event) => { setSortBy(event.target.value); setOffset(0); }}><option value="newest">Newest</option><option value="relevance">Relevance</option></select></label>
          </div>
          {(query || location || kind || mode || employmentType || postedWithinDays || sortBy !== "newest") && <div className="mt-3 flex flex-wrap items-center gap-2"><span className="text-xs text-slate-500 dark:text-slate-400">Active filters</span>{query && <Badge variant="secondary">Keyword: {query}<button aria-label="Remove keyword filter" className="ml-1" onClick={() => { setQuery(""); setQueryInput(""); setOffset(0); }}><X className="size-3" /></button></Badge>}{location && <Badge variant="secondary">Location: {location}<button aria-label="Remove location filter" className="ml-1" onClick={() => { setLocation(""); setLocationInput(""); setOffset(0); }}><X className="size-3" /></button></Badge>}{kind && <Badge variant="secondary">{TYPES.find((item) => item.value === kind)?.label}<button aria-label="Remove type filter" className="ml-1" onClick={() => setKind("")}><X className="size-3" /></button></Badge>}{mode && <Badge variant="secondary">{MODES.find((item) => item.value === mode)?.label}<button aria-label="Remove workplace filter" className="ml-1" onClick={() => setMode("")}><X className="size-3" /></button></Badge>}{employmentType && <Badge variant="secondary">{EMPLOYMENT_TYPES.find((item) => item.value === employmentType)?.label}<button aria-label="Remove employment type filter" className="ml-1" onClick={() => setEmploymentType("")}><X className="size-3" /></button></Badge>}{postedWithinDays && <Badge variant="secondary">{POSTED_WINDOWS.find((item) => item.value === postedWithinDays)?.label}<button aria-label="Remove posting date filter" className="ml-1" onClick={() => setPostedWithinDays("")}><X className="size-3" /></button></Badge>}{sortBy !== "newest" && <Badge variant="secondary">Relevance<button aria-label="Remove relevance sort" className="ml-1" onClick={() => setSortBy("newest")}><X className="size-3" /></button></Badge>}<Button variant="link" size="sm" onClick={clearFilters}>Clear all</Button></div>}
        </div>

        {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><div className="flex items-start gap-2"><CircleAlert className="mt-0.5 size-4 shrink-0" /><div className="flex-1">{error}<div className="mt-3"><Button size="sm" variant="outline" onClick={() => void loadJobs()}>Try again</Button></div></div></div></div>}
        {applicationError && <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{applicationError}<button className="ml-2 underline" onClick={() => setApplicationError("")}>Dismiss</button></div>}
        {loading ? <div aria-label="Loading opportunities" className="space-y-3">{[1,2,3].map((n) => <div key={n} className="h-48 animate-pulse rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900" />)}</div>
          : !error && result.items.length === 0 ? <Card className="border-dashed"><CardContent className="flex flex-col items-center py-12 text-center"><BriefcaseBusiness className="size-9 text-slate-300 dark:text-slate-600" /><h3 className="mt-4 font-semibold text-slate-900 dark:text-slate-100">No opportunities found</h3><p className="mt-2 max-w-sm text-sm leading-6 text-slate-500 dark:text-slate-400">Try a different keyword or clear some filters to see more opportunities.</p><Button variant="outline" className="mt-4" onClick={clearFilters}>Clear filters</Button></CardContent></Card>
          : result.items.map((job) => <OpportunityCard key={job.id} job={job} selected={job.id === selectedId} saved={savedIds.has(job.id)} onToggleSave={toggleSavedJob} onSelect={() => { setSelectedId(job.id); if (window.matchMedia("(max-width: 1279px)").matches) navigate(`/jobs/${encodeURIComponent(job.id)}`); }} />)}
        <div className="flex items-center justify-between border-t border-slate-200 dark:border-slate-800 pt-4">
          <span className="text-xs text-slate-500 dark:text-slate-400">Page size {PAGE_SIZE}</span>
          <div className="flex gap-2"><Button variant="outline" size="sm" disabled={offset <= 0 || loading} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}><ChevronLeft className="size-4" /> Previous</Button><Button variant="outline" size="sm" disabled={loading || !result.hasMore} onClick={() => setOffset(offset + PAGE_SIZE)}>Next <ChevronRight className="size-4" /></Button></div>
        </div>
      </section>

      <aside className="hidden min-w-0 xl:block">
        <div className="sticky top-4 space-y-3">
          {selected && !error ? <DetailPanel job={selected} account={account} appliedIds={appliedIds} saved={savedIds.has(selected.id)} onApply={apply} onToggleSave={toggleSavedJob} applying={applying} />
            : deepLinkError ? <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">{deepLinkError}</div>
            : <div className="flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 p-8 text-center"><BriefcaseBusiness className="size-8 text-slate-300 dark:text-slate-600" /><p className="mt-3 font-medium text-slate-800 dark:text-slate-200">Select an opportunity</p><p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Role details and application options will appear here.</p></div>}
          <p className="px-1 text-xs leading-5 text-slate-500 dark:text-slate-400">Public listings are sourced from Kairos. Campus-linked opportunities are kept in the eligible campus recruitment workflow.</p>
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
  const [isSaved, setIsSaved] = useState(false);
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
    if (!account?.roles?.some((role) => role.toUpperCase() === "STUDENT")) {
      setIsSaved(false);
      return;
    }
    const controller = new AbortController();
    apiRequest<{ items: Opportunity[] }>("/students/saved-jobs", { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setIsSaved((data.items || []).some((item) => item.id === jobId)); })
      .catch(() => { /* Keep job details usable if saved-job state cannot be loaded. */ });
    return () => controller.abort();
  }, [account, jobId]);
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
  const toggleSaved = async (item: Opportunity) => {
    if (!account) {
      window.location.assign("/auth/auth2/login");
      return;
    }
    if (!account.roles.some((role) => role.toUpperCase() === "STUDENT")) {
      setActionError("Saved jobs are available to student accounts.");
      return;
    }
    setActionError("");
    try {
      await apiRequest(`/students/saved-jobs/${encodeURIComponent(item.id)}`, { method: isSaved ? "DELETE" : "POST" });
      setIsSaved(!isSaved);
    } catch (err) {
      setActionError(errorMessage(err));
    }
  };

  return <main className="mx-auto max-w-4xl space-y-4 py-2"><Link to="/jobs" className="inline-flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:text-slate-100"><ArrowLeft className="size-4" /> Back to opportunities</Link>{loading ? <div className="h-96 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900" /> : error ? <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-800">{error}<div className="mt-3"><Button variant="outline" onClick={() => window.location.assign("/jobs")}>Return to search</Button></div></div> : job ? <><h1 className="sr-only">{job.title}</h1>{actionError && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{actionError}</div>}<DetailPanel job={job} account={account} appliedIds={appliedIds} saved={isSaved} onApply={apply} onToggleSave={toggleSaved} applying={applying} /></> : null}</main>;
}
