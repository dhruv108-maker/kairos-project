import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { ArrowLeft, ArrowUpRight, BriefcaseBusiness, Building2, CalendarDays, CheckCircle2, ChevronRight, Clock3, ExternalLink, Filter, MapPin, RefreshCw, Search, SlidersHorizontal, Sparkles, X } from "lucide-react";
import { apiRequest, ApiError } from "@/api/kairos-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

type Company = { id?: string; name?: string | null; website?: string | null };
type Opportunity = {
  id: string;
  title: string;
  summary?: string | null;
  description?: string | null;
  location?: string | null;
  application_deadline?: string | null;
  starts_on?: string | null;
  ends_on?: string | null;
  is_active?: boolean;
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
  openings?: number | null;
  required_skills?: string[] | null;
  preferred_skills?: string[] | null;
  education_requirements?: string | null;
  public_application_url?: string | null;
  created_at?: string | null;
  company?: Company | null;
};
type JobResponse = { items: Opportunity[]; limit: number; offset: number; hasMore?: boolean };

const PAGE_SIZE = 12;
const typeLabel = (value?: string | null) => (value || "Opportunity").replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
const prettyDate = (value?: string | null) => {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(date);
};
const salaryLabel = (job: Opportunity) => {
  if (!job.compensation_visible || (job.compensation_min == null && job.compensation_max == null)) return null;
  const currency = job.compensation_currency || "INR";
  const format = (amount: number | string) => new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(amount));
  const range = job.compensation_min != null && job.compensation_max != null
    ? `${format(job.compensation_min)} – ${format(job.compensation_max)}`
    : format((job.compensation_min ?? job.compensation_max) as number | string);
  return `${range}${job.compensation_period ? ` / ${job.compensation_period.toLowerCase()}` : ""}`;
};

function CompanyMark({ name }: { name?: string | null }) {
  const initials = (name || "Company").trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  return <div aria-label={name || "Company"} className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-teal-50 text-sm font-bold tracking-tight text-teal-800">{initials || "C"}</div>;
}

function OpportunityCard({ job, selected, onSelect }: { job: Opportunity; selected: boolean; onSelect: () => void }) {
  const companyName = job.company?.name || "Employer";
  const skills = (job.required_skills || []).filter(Boolean).slice(0, 3);
  return (
    <article className={`group relative rounded-2xl border bg-white p-5 transition-all duration-200 hover:border-teal-200 hover:shadow-[0_8px_28px_rgba(15,23,42,0.06)] ${selected ? "border-teal-300 shadow-[0_0_0_1px_rgba(13,148,136,0.12)]" : "border-slate-200"}`}>
      <button type="button" onClick={onSelect} aria-label={`View ${job.title} details`} className="absolute inset-0 z-0 rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2" />
      <div className="relative z-10 flex gap-3 pointer-events-none">
        <CompanyMark name={companyName} />
        <div className="min-w-0 flex-1 pt-0.5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary" className="rounded-md bg-teal-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-teal-800 hover:bg-teal-50">{typeLabel(job.opportunity_type)}</Badge>
            {job.work_mode && <span className="text-xs text-slate-500">{typeLabel(job.work_mode)}</span>}
          </div>
          <h2 className="mt-2 text-[17px] font-semibold leading-snug tracking-[-0.02em] text-slate-900">{job.title}</h2>
          <p className="mt-1 flex items-center gap-1.5 text-sm font-medium text-slate-600"><Building2 className="h-3.5 w-3.5 shrink-0" /> <span className="truncate">{companyName}</span>{job.department && <span className="truncate text-slate-400">· {job.department}</span>}</p>
        </div>
        <ChevronRight className={`mt-1 h-4 w-4 shrink-0 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-teal-700 ${selected ? "text-teal-700" : ""}`} />
      </div>
      <p className="relative z-10 pointer-events-none mt-4 line-clamp-2 text-sm leading-6 text-slate-600">{job.summary || job.description || "Explore the role details and application requirements."}</p>
      <div className="relative z-10 mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-500 pointer-events-none">
        {job.location && <span className="inline-flex items-center gap-1.5"><MapPin className="h-3.5 w-3.5" />{job.location}</span>}
        {job.application_deadline && <span className="inline-flex items-center gap-1.5"><CalendarDays className="h-3.5 w-3.5" />Apply by {prettyDate(job.application_deadline)}</span>}
        {job.experience_min_years != null && <span className="inline-flex items-center gap-1.5"><BriefcaseBusiness className="h-3.5 w-3.5" />{job.experience_min_years}{job.experience_max_years != null ? `–${job.experience_max_years}` : "+"} yrs</span>}
      </div>
      {skills.length > 0 && <div className="relative z-10 mt-4 flex flex-wrap gap-1.5 pointer-events-none">{skills.map((skill) => <span key={skill} className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] text-slate-600">{skill}</span>)}</div>}
      <Separator className="relative z-10 my-4" />
      <div className="relative z-10 flex items-center justify-between gap-3 pointer-events-none">
        <div className="min-w-0">{salaryLabel(job) ? <p className="truncate text-sm font-semibold text-slate-900">{salaryLabel(job)}</p> : <p className="text-xs text-slate-500">Compensation not disclosed</p>}<p className="mt-0.5 text-[11px] text-slate-400">{job.created_at ? `Listed ${prettyDate(job.created_at)}` : "Opportunity listing"}</p></div>
        <span className="inline-flex shrink-0 items-center gap-1.5 text-sm font-semibold text-teal-800">View details <ArrowUpRight className="h-4 w-4" /></span>
      </div>
    </article>
  );
}

function JobSkeleton() {
  return <div className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex gap-3"><Skeleton className="h-12 w-12 rounded-xl" /><div className="flex-1 space-y-2"><Skeleton className="h-4 w-24" /><Skeleton className="h-5 w-3/4" /><Skeleton className="h-4 w-1/2" /></div></div><Skeleton className="mt-5 h-4 w-full" /><Skeleton className="mt-2 h-4 w-4/5" /><Skeleton className="mt-5 h-8 w-2/3" /></div>;
}

export default function JobsHub() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedJobId = useRef(searchParams.get("job") || "");
  const [query, setQuery] = useState(searchParams.get("q") || "");
  const [location, setLocation] = useState(searchParams.get("location") || "");
  const [kind, setKind] = useState(searchParams.get("opportunity_type") || "");
  const [workMode, setWorkMode] = useState(searchParams.get("work_mode") || "");
  const [offset, setOffset] = useState(Number(searchParams.get("offset") || 0));
  const [data, setData] = useState<JobResponse | null>(null);
  const [selectedId, setSelectedId] = useState(searchParams.get("job") || "");
  const [detail, setDetail] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applyMessage, setApplyMessage] = useState("");
  const [requestKey, setRequestKey] = useState(0);

  const loadJobs = useCallback(async (signal: AbortSignal) => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ limit: String(PAGE_SIZE + 1), offset: String(offset) });
    if (query.trim()) params.set("q", query.trim());
    if (location.trim()) params.set("location", location.trim());
    if (kind) params.set("opportunity_type", kind);
    if (workMode) params.set("work_mode", workMode);
    try {
      const result = await apiRequest<JobResponse>(`/jobs?${params.toString()}`, { signal });
      if (signal.aborted) return;
      setData(result);
      setSelectedId((current) => result.items.some((item) => item.id === current) || (current && current === requestedJobId.current) ? current : result.items[0]?.id || "");
    } catch (err) {
      if (signal.aborted) return;
      setError(err instanceof Error ? err.message : "We couldn't load opportunities. Please try again.");
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [query, location, kind, workMode, offset, requestKey]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void loadJobs(controller.signal), 250);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [loadJobs]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (query.trim()) params.set("q", query.trim());
    if (location.trim()) params.set("location", location.trim());
    if (kind) params.set("opportunity_type", kind);
    if (workMode) params.set("work_mode", workMode);
    if (offset) params.set("offset", String(offset));
    if (selectedId) params.set("job", selectedId);
    setSearchParams(params, { replace: true });
  }, [query, location, kind, workMode, offset, selectedId, setSearchParams]);

  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    const controller = new AbortController();
    setDetailLoading(true);
    setDetailError("");
    apiRequest<Opportunity>(`/jobs/${encodeURIComponent(selectedId)}`, { signal: controller.signal })
      .then((job) => { if (!controller.signal.aborted) setDetail(job); })
      .catch((err) => { if (!controller.signal.aborted) { const fallback = data?.items.find((item) => item.id === selectedId); if (err instanceof ApiError && err.status === 404 && fallback) { setDetail(fallback); setDetailError(""); } else { setDetail(null); setDetailError(err instanceof Error ? err.message : "Unable to load this opportunity."); } } })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false); });
    return () => controller.abort();
  }, [selectedId, data]);

  const activeFilters = useMemo(() => [
    ...(query.trim() ? [{ label: `Keyword: ${query.trim()}`, clear: () => setQuery("") }] : []),
    ...(location.trim() ? [{ label: `Location: ${location.trim()}`, clear: () => setLocation("") }] : []),
    ...(kind ? [{ label: typeLabel(kind), clear: () => setKind("") }] : []),
    ...(workMode ? [{ label: typeLabel(workMode), clear: () => setWorkMode("") }] : []),
  ], [query, location, kind, workMode]);

  const clearFilters = () => { setQuery(""); setLocation(""); setKind(""); setWorkMode(""); setOffset(0); };
  const submitSearch = (event: FormEvent) => { event.preventDefault(); setOffset(0); };
  const currentJob = detail || data?.items.find((item) => item.id === selectedId) || null;
  const companyName = currentJob?.company?.name || "Employer";
  const retry = () => setRequestKey((value) => value + 1);
  const applyToOpportunity = async () => {
    if (!currentJob) return;
    setApplying(true);
    setApplyMessage("");
    try {
      await apiRequest(`/internships/opportunities/${encodeURIComponent(currentJob.id)}/applications`, { method: "POST" });
      setApplyMessage("Your application was submitted successfully.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setApplyMessage("Sign in with your student account to apply.");
      } else if (err instanceof ApiError && err.status === 409) {
        setApplyMessage("You have already applied to this opportunity.");
      } else {
        setApplyMessage(err instanceof Error ? err.message : "We could not submit your application.");
      }
    } finally { setApplying(false); }
  };
  return (
    <main className="min-h-screen bg-[#fafbfc] text-slate-900">
      <div className="mx-auto max-w-[1440px] px-4 pb-12 pt-7 sm:px-6 lg:px-8">
        <div className="mb-7 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm text-slate-500"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-800 text-white"><BriefcaseBusiness className="h-4 w-4" /></span><span>Kairos</span><ChevronRight className="h-3.5 w-3.5" /><span className="font-medium text-slate-800">Careers</span></div>
          <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500 sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-teal-600" /> Opportunities from verified, active listings</div>
        </div>
        <section className="mb-8">
          <div className="max-w-3xl">
            <p className="mb-3 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-teal-800"><Sparkles className="h-3.5 w-3.5" /> Your next chapter starts here</p>
            <h1 className="text-3xl font-semibold tracking-[-0.045em] text-slate-950 sm:text-4xl lg:text-[42px]">Find your next opportunity</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">Discover internships, graduate roles, and opportunities that move your career forward.</p>
          </div>
          <form onSubmit={submitSearch} className="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-[0_5px_22px_rgba(15,23,42,0.035)] md:grid-cols-[minmax(0,1.4fr)_minmax(190px,0.8fr)_auto] md:items-center">
            <label className="flex min-w-0 items-center gap-3 px-2"><Search className="h-5 w-5 shrink-0 text-slate-400" /><span className="sr-only">Job title, skill, keyword, or company</span><Input value={query} onChange={(event) => { setQuery(event.target.value); setOffset(0); }} placeholder="Job title, skill, keyword, or company" className="h-11 border-0 bg-transparent px-0 shadow-none focus-visible:ring-0" /></label>
            <Separator orientation="vertical" className="hidden h-8 md:block" />
            <label className="flex min-w-0 items-center gap-3 px-2"><MapPin className="h-5 w-5 shrink-0 text-slate-400" /><span className="sr-only">Location</span><Input value={location} onChange={(event) => { setLocation(event.target.value); setOffset(0); }} placeholder="City or remote" className="h-11 border-0 bg-transparent px-0 shadow-none focus-visible:ring-0" /></label>
            <Button type="submit" className="h-11 rounded-xl bg-teal-800 px-6 text-white hover:bg-teal-900"><Search className="mr-2 h-4 w-4" /> Search roles</Button>
          </form>
        </section>

        <nav aria-label="Career navigation" className="mb-6 flex flex-wrap items-center gap-2 border-b border-slate-200 pb-4">
          <Button variant="secondary" className="rounded-full bg-teal-50 text-teal-900 hover:bg-teal-100"><Search className="mr-2 h-4 w-4" />Explore opportunities</Button>
          <Link to="/jobs/applications" className="inline-flex h-9 items-center rounded-full px-4 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"><CheckCircle2 className="mr-2 h-4 w-4" />My applications</Link>
          <span className="ml-auto hidden text-xs text-slate-500 sm:inline">Find a role that fits your next move</span>
        </nav>

        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.04fr)_minmax(390px,0.96fr)]">
          <section aria-label="Opportunity results" className="min-w-0">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div><h2 className="text-lg font-semibold tracking-tight text-slate-900">Explore opportunities</h2><p className="mt-1 text-xs text-slate-500">{loading ? "Finding relevant roles…" : data ? `Showing ${data.items.length ? offset + 1 : 0}–${offset + data.items.length} opportunities` : "Search current openings"}</p></div>
              <Button variant="outline" size="sm" className="rounded-lg border-slate-200 bg-white xl:hidden" onClick={() => setFiltersOpen((value) => !value)}><SlidersHorizontal className="mr-2 h-4 w-4" />Filters</Button>
            </div>
            <div className={`mb-4 rounded-xl border border-slate-200 bg-white p-3 ${filtersOpen ? "block" : "hidden xl:block"}`}>
              <div className="mb-2 flex items-center justify-between"><span className="flex items-center gap-2 text-xs font-semibold text-slate-700"><Filter className="h-3.5 w-3.5" /> Refine results</span>{activeFilters.length > 0 && <button type="button" onClick={clearFilters} className="text-xs font-medium text-teal-800 hover:underline">Clear all</button>}</div>
              <div className="grid gap-2 sm:grid-cols-2">
                <label className="text-xs text-slate-500">Opportunity type<select aria-label="Opportunity type" value={kind} onChange={(event) => { setKind(event.target.value); setOffset(0); }} className="mt-1.5 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"><option value="">All types</option><option value="JOB">Full-time & jobs</option><option value="INTERNSHIP">Internships</option></select></label>
                <label className="text-xs text-slate-500">Work arrangement<select aria-label="Work arrangement" value={workMode} onChange={(event) => { setWorkMode(event.target.value); setOffset(0); }} className="mt-1.5 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"><option value="">Any arrangement</option><option value="REMOTE">Remote</option><option value="HYBRID">Hybrid</option><option value="ONSITE">On-site</option></select></label>
              </div>
              {activeFilters.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{activeFilters.map((filter) => <button key={filter.label} type="button" onClick={() => { filter.clear(); setOffset(0); }} className="inline-flex items-center gap-1 rounded-full border border-teal-100 bg-teal-50 px-2.5 py-1 text-xs text-teal-900">{filter.label}<X className="h-3 w-3" /></button>)}</div>}
            </div>

            {error && <Card className="rounded-2xl border-rose-200 p-6"><div className="flex items-start gap-3"><div className="rounded-lg bg-rose-50 p-2 text-rose-700"><RefreshCw className="h-5 w-5" /></div><div className="flex-1"><h3 className="font-semibold text-slate-900">We couldn't load opportunities</h3><p className="mt-1 text-sm text-slate-600">{error}</p><Button onClick={retry} variant="outline" size="sm" className="mt-4">Try again</Button></div></div></Card>}
            {!error && loading && <div className="space-y-3">{Array.from({ length: 3 }, (_, index) => <JobSkeleton key={index} />)}</div>}
            {!error && !loading && data?.items.length === 0 && <Card className="rounded-2xl border-dashed border-slate-300 bg-white p-10 text-center"><div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-500"><Search className="h-5 w-5" /></div><h3 className="mt-4 text-base font-semibold">No opportunities match your search</h3><p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-slate-500">Try a different keyword or location, or clear your filters to explore more roles.</p><Button variant="outline" onClick={clearFilters} className="mt-5 rounded-xl">Clear filters</Button></Card>}
            {!error && !loading && data && data.items.length > 0 && <div className="space-y-3">{data.items.map((job) => <OpportunityCard key={job.id} job={job} selected={job.id === selectedId} onSelect={() => setSelectedId(job.id)} />)}</div>}
            {!error && !loading && data && <div className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3"><span className="text-xs text-slate-500">Page {Math.floor(offset / PAGE_SIZE) + 1}</span><div className="flex gap-2"><Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}><ArrowLeft className="mr-1.5 h-3.5 w-3.5" />Previous</Button><Button variant="outline" size="sm" disabled={!data.hasMore} onClick={() => setOffset(offset + PAGE_SIZE)}>Next<ChevronRight className="ml-1.5 h-3.5 w-3.5" /></Button></div></div>}
            {!detailLoading && !detailError && currentJob && <Card className="mt-4 rounded-2xl border-slate-200 bg-white p-5 xl:hidden"><div className="flex items-start gap-3"><CompanyMark name={companyName} /><div className="min-w-0"><h2 className="text-lg font-semibold leading-snug">{currentJob.title}</h2><p className="mt-1 text-sm text-slate-600">{companyName}{currentJob.location ? " · " + currentJob.location : ""}</p></div></div><Separator className="my-4" /><h3 className="text-sm font-semibold">About the opportunity</h3><p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">{currentJob.description || currentJob.summary || "No additional description was provided."}</p>{currentJob.required_skills && currentJob.required_skills.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{currentJob.required_skills.slice(0, 8).map((skill) => <Badge key={skill} variant="secondary" className="bg-slate-100 text-slate-700">{skill}</Badge>)}</div>}{currentJob.public_application_url ? <a href={currentJob.public_application_url} target="_blank" rel="noopener noreferrer" className="mt-5 inline-flex h-10 items-center justify-center rounded-lg bg-teal-800 px-4 text-sm font-medium text-white hover:bg-teal-900">Apply on company website <ExternalLink className="ml-2 h-4 w-4" /></a> : <Button disabled={applying} onClick={applyToOpportunity} className="mt-5 rounded-xl bg-teal-800 text-white hover:bg-teal-900">{applying ? "Submitting…" : "Apply through Kairos"}</Button>}{applyMessage && <p role="status" className="mt-3 text-sm text-slate-600">{applyMessage}</p>}</Card>}
          </section>

          <aside aria-label="Selected opportunity details" className="hidden min-w-0 xl:block">
            <div className="sticky top-5">
              {detailLoading && <Card className="rounded-2xl p-6"><Skeleton className="h-14 w-14 rounded-xl" /><Skeleton className="mt-5 h-6 w-3/4" /><Skeleton className="mt-3 h-4 w-1/2" /><Skeleton className="mt-8 h-24 w-full" /></Card>}
              {!detailLoading && detailError && <Card className="rounded-2xl border-rose-200 p-6"><h3 className="font-semibold">Details unavailable</h3><p className="mt-2 text-sm text-slate-600">{detailError}</p><Button variant="outline" size="sm" className="mt-4" onClick={() => setSelectedId(selectedId)}>Retry details</Button></Card>}
              {!detailLoading && !detailError && currentJob && <Card className="overflow-hidden rounded-2xl border-slate-200 bg-white shadow-[0_5px_24px_rgba(15,23,42,0.04)]">
                <div className="border-b border-slate-100 bg-gradient-to-br from-white via-white to-teal-50/70 p-6">
                  <div className="flex items-start justify-between gap-4"><CompanyMark name={companyName} />{currentJob.application_deadline && <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-800"><Clock3 className="h-3 w-3" />Due {prettyDate(currentJob.application_deadline)}</span>}</div>
                  <h2 className="mt-5 text-2xl font-semibold leading-tight tracking-[-0.035em] text-slate-950">{currentJob.title}</h2>
                  <p className="mt-2 text-sm font-medium text-slate-600">{companyName}</p>
                  <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-500">{currentJob.location && <span className="inline-flex items-center gap-1.5"><MapPin className="h-3.5 w-3.5" />{currentJob.location}</span>}{currentJob.work_mode && <span>{typeLabel(currentJob.work_mode)}</span>}{currentJob.employment_type && <span>{typeLabel(currentJob.employment_type)}</span>}</div>
                  {salaryLabel(currentJob) && <p className="mt-4 text-sm font-semibold text-slate-900">{salaryLabel(currentJob)}</p>}
                  <div className="mt-5 flex flex-wrap gap-2">{currentJob.public_application_url ? <a href={currentJob.public_application_url} target="_blank" rel="noopener noreferrer" className="inline-flex h-9 items-center justify-center rounded-lg bg-teal-800 px-3 text-sm font-medium text-white transition hover:bg-teal-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-700 focus-visible:ring-offset-2">Apply on company website <ExternalLink className="ml-2 h-4 w-4" /></a> : <Button disabled={applying} onClick={applyToOpportunity} className="rounded-xl bg-teal-800 text-white hover:bg-teal-900">{applying ? "Submitting…" : "Apply through Kairos"}</Button>}</div>
                  {currentJob.public_application_url && <p className="mt-2 text-[11px] leading-5 text-slate-500">You'll continue on the employer's website. Kairos does not submit or track this external application.</p>}
                  {applyMessage && <p role="status" className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">{applyMessage}{applyMessage.includes("Sign in") && <a href="/auth/auth2/login" className="ml-1 font-semibold text-teal-800 underline">Sign in</a>}</p>}
                </div>
                <div className="space-y-6 p-6">
                  <section><h3 className="text-sm font-semibold text-slate-900">About the opportunity</h3><p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">{currentJob.description || currentJob.summary || "No additional description was provided."}</p></section>
                  {currentJob.education_requirements && <section><h3 className="text-sm font-semibold text-slate-900">Education requirements</h3><p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">{currentJob.education_requirements}</p></section>}
                  {((currentJob.required_skills || []).length > 0 || (currentJob.preferred_skills || []).length > 0) && <section><h3 className="text-sm font-semibold text-slate-900">Skills</h3>{currentJob.required_skills && currentJob.required_skills.length > 0 && <><p className="mt-2 text-xs font-medium text-slate-500">Required</p><div className="mt-2 flex flex-wrap gap-2">{currentJob.required_skills.map((skill) => <Badge key={skill} variant="secondary" className="rounded-md bg-slate-100 font-normal text-slate-700">{skill}</Badge>)}</div></>}{currentJob.preferred_skills && currentJob.preferred_skills.length > 0 && <><p className="mt-3 text-xs font-medium text-slate-500">Preferred</p><div className="mt-2 flex flex-wrap gap-2">{currentJob.preferred_skills.map((skill) => <Badge key={skill} variant="outline" className="rounded-md font-normal">{skill}</Badge>)}</div></>}</section>}
                  <section className="rounded-xl border border-slate-200 bg-slate-50 p-4"><h3 className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">Listing details</h3><dl className="mt-3 space-y-3 text-sm">{currentJob.application_deadline && <div className="flex justify-between gap-4"><dt className="text-slate-500">Deadline</dt><dd className="text-right font-medium text-slate-800">{prettyDate(currentJob.application_deadline)}</dd></div>}{currentJob.openings != null && <div className="flex justify-between gap-4"><dt className="text-slate-500">Openings</dt><dd className="font-medium text-slate-800">{currentJob.openings}</dd></div>}{currentJob.experience_min_years != null && <div className="flex justify-between gap-4"><dt className="text-slate-500">Experience</dt><dd className="font-medium text-slate-800">{currentJob.experience_min_years}{currentJob.experience_max_years != null ? `–${currentJob.experience_max_years}` : "+"} years</dd></div>}</dl></section>
                </div>
              </Card>}
              {!detailLoading && !detailError && !currentJob && <Card className="rounded-2xl border-dashed border-slate-300 p-10 text-center"><BriefcaseBusiness className="mx-auto h-8 w-8 text-slate-300" /><h3 className="mt-4 font-semibold">Choose an opportunity</h3><p className="mt-2 text-sm leading-6 text-slate-500">Select a role from the list to see its details and application instructions.</p></Card>}
              <p className="mt-4 px-2 text-[11px] leading-5 text-slate-400">Campus-linked opportunities are shown through eligible recruitment-drive workflows, not this public discovery list.</p>
            </div>
          </aside>
        </div>
        <footer className="mt-10 flex flex-col gap-2 border-t border-slate-200 pt-5 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between"><span>Kairos Careers · Built around real opportunities, clear requirements, and trusted workflows.</span><span className="inline-flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-teal-700" /> Your career, connected</span></footer>
      </div>
    </main>
  );
}
