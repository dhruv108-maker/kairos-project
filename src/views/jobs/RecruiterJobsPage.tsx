import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";
import { ArrowLeft, BriefcaseBusiness, Check, ChevronLeft, ChevronRight, CircleAlert, LoaderCircle, Plus, RefreshCw, Save, Send, X } from "lucide-react";
import { ApiError, apiRequest } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type Org = { id: string; display_name: string; status: string; role?: string };
type Job = { id: string; title: string; summary?: string | null; description: string; location: string; application_deadline: string; lifecycle_status: string; opportunity_type: string; employment_type: string; work_mode: string; compensation_min?: number | string | null; compensation_max?: number | string | null; compensation_currency?: string; compensation_period?: string; compensation_visible?: boolean; required_skills?: string[]; preferred_skills?: string[]; education_requirements?: string | null; public_application_url?: string | null; openings?: number; created_at?: string; };
type Applicant = { id: string; opportunity_id: string; job_title: string; student_id: string; applicant_name: string; applicant_email: string; legacy_status: string; stage: string; applied_at?: string };
type ApplicationDetail = { id: string; opportunity_id: string; job_title: string; applicant?: { name: string; email: string } | null; legacy_status: string; stage: string; applied_at?: string; stage_history: Array<{ from_stage: string; to_stage: string; note?: string | null; created_at: string }> };
type Note = { id: string; body: string; created_at: string };
const stages = ["SUBMITTED", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW", "OFFER", "HIRED", "REJECTED", "WITHDRAWN"];
const transitions: Record<string, string[]> = { SUBMITTED: ["UNDER_REVIEW", "REJECTED", "WITHDRAWN"], UNDER_REVIEW: ["SHORTLISTED", "INTERVIEW", "REJECTED", "WITHDRAWN"], SHORTLISTED: ["INTERVIEW", "OFFER", "REJECTED", "WITHDRAWN"], INTERVIEW: ["SHORTLISTED", "OFFER", "REJECTED", "WITHDRAWN"], OFFER: ["HIRED", "REJECTED", "WITHDRAWN"], HIRED: [], REJECTED: [], WITHDRAWN: [] };
const lifecycle: Record<string, string[]> = { DRAFT: ["publish", "archive"], PUBLISHED: ["pause", "close"], PAUSED: ["resume", "close", "archive"], CLOSED: ["reopen", "archive"], ARCHIVED: [] };
const lifecycleLabel: Record<string, string> = { DRAFT: "Draft", PUBLISHED: "Published", PAUSED: "Paused", CLOSED: "Closed", ARCHIVED: "Archived" };
const blankJob = () => ({ title: "", summary: "", description: "", opportunity_type: "JOB", employment_type: "FULL_TIME", work_mode: "ONSITE", location: "", department: "", application_deadline: "", starts_on: "", ends_on: "", experience_min_years: "", experience_max_years: "", compensation_min: "", compensation_max: "", compensation_currency: "INR", compensation_period: "YEAR", compensation_visible: true, openings: "1", required_skills: "", preferred_skills: "", education_requirements: "", public_application_url: "" });
type JobForm = ReturnType<typeof blankJob>;
const fieldClass = "w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-600/15";
const labelClass = "mb-1.5 block text-sm font-medium text-slate-700";
function pretty(value?: string | null) { return (value || "").toLowerCase().replace(/_/g, " ").replace(/^./, c => c.toUpperCase()); }
function message(error: unknown) { if (error instanceof ApiError) return error.status === 403 ? "Your account does not have permission for this action." : error.status === 409 ? "The resource changed or this action is not valid for its current state. Refresh and try again." : error.message; return "Kairos could not be reached. Check your connection and retry."; }
function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) { return <div><label className={labelClass}>{label}</label>{children}{hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}</div>; }

export default function RecruiterJobsPage() {
  const { account, isLoading: authLoading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();
  const isStudentOrFaculty = account?.roles.some(role => ["STUDENT", "FACULTY"].includes(role.toUpperCase()));
  const allowed = account?.roles.some(role => ["EMPLOYER", "RECRUITER", "EMPLOYER_ADMIN", "ADMIN"].includes(role.toUpperCase()));
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [orgId, setOrgId] = useState("");
  const [orgLoading, setOrgLoading] = useState(true);
  const [orgError, setOrgError] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState<JobForm>(blankJob());
  const [initialForm, setInitialForm] = useState("");
  const [formLoading, setFormLoading] = useState(false);
  const [applicants, setApplicants] = useState<Applicant[]>([]);
  const [appLoading, setAppLoading] = useState(false);
  const [stageFilter, setStageFilter] = useState("");
  const [jobFilter, setJobFilter] = useState("");
  const [detail, setDetail] = useState<ApplicationDetail | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [noteText, setNoteText] = useState("");
  const [stageNote, setStageNote] = useState("");
  const [newStage, setNewStage] = useState("");

  const section = location.pathname.endsWith("/applications") ? "applications"
    : location.pathname.endsWith("/create") ? "create"
    : location.pathname.endsWith("/edit") || /\/jobs\/[^/]+\/edit$/.test(location.pathname) ? "edit"
    : /\/applications\/[^/]+$/.test(location.pathname) ? "application-detail" : "list";
  const selectedJobId = params.jobId || (section === "edit" ? location.pathname.split("/").at(-2) : undefined);
  const selectedApplicationId = params.applicationId || (section === "application-detail" ? location.pathname.split("/").at(-1) : undefined);
  const org = orgs.find(item => item.id === orgId);

  const loadOrgs = useCallback(async () => {
    setOrgLoading(true); setOrgError("");
    try {
      const result = await apiRequest<{ items: Org[] }>("/employers/me/organizations");
      const available = result.items || [];
      setOrgs(available);
      setOrgId(current => current && available.some(item => item.id === current) ? current : available[0]?.id || "");
      if (!available.length) setOrgError("No employer organization is linked to this account. Complete employer registration or ask your organization owner to add you.");
    } catch (e) { setOrgError(message(e)); } finally { setOrgLoading(false); }
  }, []);
  useEffect(() => { if (account && allowed && !isStudentOrFaculty) void loadOrgs(); }, [account, allowed, isStudentOrFaculty, loadOrgs]);

  const loadJobs = useCallback(async () => {
    if (!orgId) return;
    setJobsLoading(true); setError("");
    try {
      const data = await apiRequest<{ items: Job[]; limit: number; offset: number }>(`/employers/organizations/${encodeURIComponent(orgId)}/jobs?limit=20&offset=${offset}`);
      setJobs(data.items || []); setHasMore((data.items || []).length === 20);
    } catch (e) { setError(message(e)); } finally { setJobsLoading(false); }
  }, [orgId, offset]);
  useEffect(() => { if (section === "list" || section === "edit" || section === "applications") void loadJobs(); }, [section, loadJobs]);

  const loadApplications = useCallback(async () => {
    if (!orgId) return;
    setAppLoading(true); setError("");
    try {
      const query = new URLSearchParams({ limit: "25", offset: String(offset) });
      if (stageFilter) query.set("stage", stageFilter);
      if (jobFilter) query.set("job_id", jobFilter);
      const data = await apiRequest<{ items: Applicant[] }>(`/employers/organizations/${encodeURIComponent(orgId)}/applications?${query}`);
      setApplicants(data.items || []); setHasMore((data.items || []).length === 25);
    } catch (e) { setError(message(e)); } finally { setAppLoading(false); }
  }, [orgId, offset, stageFilter, jobFilter]);
  useEffect(() => { if (section === "applications") void loadApplications(); }, [section, loadApplications]);

  useEffect(() => {
    if (section !== "create" && section !== "edit") return;
    let active = true;
    const load = async () => {
      setFormLoading(true); setError(""); setNotice("");
      try {
        if (section === "edit" && orgId && selectedJobId) {
          const job = await apiRequest<Job>(`/employers/organizations/${encodeURIComponent(orgId)}/jobs/${encodeURIComponent(selectedJobId)}`);
          const next: JobForm = {
            ...blankJob(), title: job.title || "", summary: job.summary || "", description: job.description || "",
            opportunity_type: job.opportunity_type || "JOB", employment_type: job.employment_type || "FULL_TIME",
            work_mode: job.work_mode || "ONSITE", location: job.location || "", department: (job as Job & { department?: string }).department || "",
            application_deadline: job.application_deadline?.slice(0, 10) || "", starts_on: (job as Job & { starts_on?: string }).starts_on?.slice(0, 10) || "",
            ends_on: (job as Job & { ends_on?: string }).ends_on?.slice(0, 10) || "",
            experience_min_years: String((job as Job & { experience_min_years?: number }).experience_min_years ?? ""),
            experience_max_years: String((job as Job & { experience_max_years?: number }).experience_max_years ?? ""),
            compensation_min: job.compensation_min == null ? "" : String(job.compensation_min), compensation_max: job.compensation_max == null ? "" : String(job.compensation_max),
            compensation_currency: job.compensation_currency || "INR", compensation_period: job.compensation_period || "YEAR",
            compensation_visible: job.compensation_visible !== false, openings: String(job.openings || 1),
            required_skills: (job.required_skills || []).join(", "), preferred_skills: (job.preferred_skills || []).join(", "),
            education_requirements: job.education_requirements || "", public_application_url: job.public_application_url || "",
          };
          if (active) { setForm(next); setInitialForm(JSON.stringify(next)); }
        } else if (section === "create" && active) { const next = blankJob(); setForm(next); setInitialForm(JSON.stringify(next)); }
      } catch (e) { if (active) setError(message(e)); }
      finally { if (active) setFormLoading(false); }
    };
    if (section === "create" || (orgId && selectedJobId)) void load();
    return () => { active = false; };
  }, [section, orgId, selectedJobId]);

  const loadApplicationDetail = useCallback(async () => {
    if (!orgId || !selectedApplicationId) return;
    setError(""); setDetail(null);
    try {
      const [item, noteResult] = await Promise.all([
        apiRequest<ApplicationDetail>(`/employers/organizations/${encodeURIComponent(orgId)}/applications/${encodeURIComponent(selectedApplicationId)}`),
        apiRequest<{ items: Note[] }>(`/employers/organizations/${encodeURIComponent(orgId)}/applications/${encodeURIComponent(selectedApplicationId)}/notes`),
      ]);
      setDetail(item); setNotes(noteResult.items || []); setNewStage(item.stage);
    } catch (e) { setError(message(e)); }
  }, [orgId, selectedApplicationId]);
  useEffect(() => { if (section === "application-detail") void loadApplicationDetail(); }, [section, loadApplicationDetail]);

  const updateField = (key: keyof JobForm, value: string | boolean) => setForm(previous => ({ ...previous, [key]: value }));
  const dirty = JSON.stringify(form) !== initialForm;
  useEffect(() => {
    if (!dirty || (section !== "edit" && section !== "create")) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty, section]);

  const saveJob = async (event: FormEvent, publishAfterSave = false) => {
    event.preventDefault();
    if (!orgId) return;
    if (section === "edit" && dirty && !window.confirm("Save changes to this listing?")) return;
    setBusy(publishAfterSave ? "publish" : "save"); setError(""); setNotice("");
    const splitSkills = (value: string) => value.split(",").map(item => item.trim()).filter(Boolean);
    const payload: Record<string, unknown> = {
      title: form.title.trim(), summary: form.summary.trim() || null, description: form.description.trim(),
      opportunity_type: form.opportunity_type, employment_type: form.employment_type, work_mode: form.work_mode,
      location: form.location.trim(), department: form.department.trim() || null,
      application_deadline: form.application_deadline, starts_on: form.starts_on || null, ends_on: form.ends_on || null,
      experience_min_years: form.experience_min_years === "" ? null : Number(form.experience_min_years),
      experience_max_years: form.experience_max_years === "" ? null : Number(form.experience_max_years),
      compensation_min: form.compensation_min === "" ? null : Number(form.compensation_min),
      compensation_max: form.compensation_max === "" ? null : Number(form.compensation_max),
      compensation_currency: form.compensation_currency, compensation_period: form.compensation_period,
      compensation_visible: form.compensation_visible, openings: Number(form.openings || 1),
      required_skills: splitSkills(form.required_skills), preferred_skills: splitSkills(form.preferred_skills),
      education_requirements: form.education_requirements.trim() || null,
      public_application_url: form.public_application_url.trim() || null,
    };
    try {
      let saved: Job;
      if (section === "edit" && selectedJobId) saved = await apiRequest<Job>(`/employers/organizations/${encodeURIComponent(orgId)}/jobs/${encodeURIComponent(selectedJobId)}`, { method: "PATCH", body: JSON.stringify(payload) });
      else saved = await apiRequest<Job>(`/employers/organizations/${encodeURIComponent(orgId)}/jobs`, { method: "POST", body: JSON.stringify(payload) });
      if (publishAfterSave) {
        const result = await apiRequest<Job>(`/employers/organizations/${encodeURIComponent(orgId)}/jobs/${encodeURIComponent(saved.id)}/publish`, { method: "POST" });
        setNotice(`Listing saved and ${pretty(result.lifecycle_status).toLowerCase()} successfully.`);
      } else setNotice("Listing saved as a draft. Publish it from My Listings when ready.");
      setInitialForm(JSON.stringify(form));
      navigate("/jobs/recruiter");
    } catch (e) { setError(message(e)); } finally { setBusy(""); }
  };

  const jobAction = async (job: Job, action: string) => {
    if (!orgId) return;
    const confirmText = action === "archive" ? "Archive this listing? It will no longer be manageable as an active listing." : action === "close" ? "Close this listing? Applications will stop." : "";
    if (confirmText && !window.confirm(confirmText)) return;
    setBusy(job.id + action); setError(""); setNotice("");
    try {
      await apiRequest(`/employers/organizations/${encodeURIComponent(orgId)}/jobs/${encodeURIComponent(job.id)}/${action}`, { method: "POST" });
      setNotice(`Listing ${action}d successfully.`); await loadJobs();
    } catch (e) { setError(message(e)); } finally { setBusy(""); }
  };

  const changeStage = async (event: FormEvent) => {
    event.preventDefault(); if (!orgId || !detail || !newStage || newStage === detail.stage) return;
    setBusy("stage"); setError("");
    try {
      await apiRequest(`/employers/organizations/${encodeURIComponent(orgId)}/applications/${encodeURIComponent(detail.id)}/stage`, { method: "POST", body: JSON.stringify({ stage: newStage, note: stageNote.trim() || null }) });
      setStageNote(""); setNotice("Applicant stage updated."); await loadApplicationDetail();
    } catch (e) { setError(message(e)); } finally { setBusy(""); }
  };
  const addNote = async (event: FormEvent) => {
    event.preventDefault(); if (!orgId || !detail || !noteText.trim()) return;
    setBusy("note"); setError("");
    try {
      await apiRequest(`/employers/organizations/${encodeURIComponent(orgId)}/applications/${encodeURIComponent(detail.id)}/notes`, { method: "POST", body: JSON.stringify({ body: noteText.trim() }) });
      setNoteText(""); const result = await apiRequest<{ items: Note[] }>(`/employers/organizations/${encodeURIComponent(orgId)}/applications/${encodeURIComponent(detail.id)}/notes`);
      setNotes(result.items || []); setNotice("Private note added.");
    } catch (e) { setError(message(e)); } finally { setBusy(""); }
  };

  if (authLoading) return <main className="mx-auto max-w-5xl p-6"><div className="h-28 animate-pulse rounded-xl bg-slate-100" /></main>;
  if (!account) return <main className="mx-auto max-w-3xl py-10"><div className="rounded-xl border border-slate-200 bg-white p-8"><h1 className="text-xl font-semibold">Recruiter sign-in required</h1><p className="mt-2 text-sm text-slate-600">Sign in with an authorized employer account to manage listings and applicants.</p><Link className="mt-5 inline-flex h-9 items-center rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground" to="/auth/auth2/login">Sign in</Link></div></main>;
  if (isStudentOrFaculty || !allowed) return <main className="mx-auto max-w-3xl py-10"><div className="rounded-xl border border-slate-200 bg-white p-8"><h1 className="text-xl font-semibold">Recruiter access required</h1><p className="mt-2 text-sm text-slate-600">This workspace is available to authorized employer organization members. Your account roles do not grant access to recruiter management.</p><Link className="mt-5 inline-flex h-9 items-center rounded-lg border border-slate-200 px-3 text-sm font-medium" to="/jobs">Explore jobs</Link></div></main>;

  const header = section === "create" ? "Create a job" : section === "edit" ? "Edit listing" : section === "applications" ? "Applications" : section === "application-detail" ? "Applicant review" : "My listings";
  return <main className="mx-auto max-w-6xl space-y-5 py-2">
    <div className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div><Link to="/jobs" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"><ArrowLeft className="size-4" /> Explore jobs</Link><h1 className="text-2xl font-semibold tracking-tight text-slate-950">{header}</h1><p className="mt-1 text-sm text-slate-500">Manage employer listings and review applicants in your organization.</p></div>
      <div className="flex flex-wrap gap-2"><Button variant={section === "list" ? "default" : "outline"} onClick={() => navigate("/jobs/recruiter")}>My listings</Button><Button variant={section === "applications" ? "default" : "outline"} onClick={() => navigate("/jobs/recruiter/applications")}>Applications</Button><Button onClick={() => navigate("/jobs/recruiter/create")}><Plus className="mr-1 size-4" />Create job</Button></div>
    </div>
    {orgs.length > 1 && <div className="flex flex-wrap items-center gap-3"><label htmlFor="recruiter-org" className="text-sm font-medium text-slate-700">Organization</label><select id="recruiter-org" className={fieldClass + " max-w-sm"} value={orgId} onChange={e => { setOrgId(e.target.value); setOffset(0); }}><option value="">Select organization</option>{orgs.map(item => <option key={item.id} value={item.id}>{item.display_name} · {pretty(item.status)}</option>)}</select></div>}
    {org && <p className="text-xs text-slate-500">Managing {org.display_name} · organization status: {pretty(org.status)}. Publishing requires an active, verified organization.</p>}
    {orgLoading && <div className="flex items-center gap-2 py-6 text-sm text-slate-500"><LoaderCircle className="size-4 animate-spin" /> Loading your employer organizations…</div>}
    {orgError && !orgLoading && <div role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{orgError}<Button variant="outline" size="sm" className="ml-3" onClick={() => void loadOrgs()}><RefreshCw className="mr-1 size-3.5" />Retry</Button></div>}
    {error && <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"><CircleAlert className="mt-0.5 size-4 shrink-0" /><span>{error}</span><button aria-label="Dismiss error" className="ml-auto" onClick={() => setError("")}><X className="size-4" /></button></div>}
    {notice && <div role="status" className="rounded-lg border border-teal-200 bg-teal-50 p-3 text-sm text-teal-900"><Check className="mr-1 inline size-4" />{notice}</div>}
    {!orgLoading && orgId && section === "list" && <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3"><p className="text-sm text-slate-600">{jobsLoading ? "Loading listings…" : `${jobs.length} listing${jobs.length === 1 ? "" : "s"} on this page`}</p><Button size="sm" variant="ghost" onClick={() => void loadJobs()} disabled={jobsLoading}><RefreshCw className={"mr-1 size-3.5 " + (jobsLoading ? "animate-spin" : "")} />Refresh</Button></div>
      {jobsLoading ? <div className="space-y-3 p-4">{[1,2,3,4].map(i => <div key={i} className="h-16 animate-pulse rounded-lg bg-slate-100" />)}</div> : jobs.length === 0 ? <div className="px-5 py-16 text-center"><BriefcaseBusiness className="mx-auto size-8 text-slate-300" /><h2 className="mt-3 font-semibold text-slate-900">No listings yet</h2><p className="mt-1 text-sm text-slate-500">Create your first listing and save it as a draft before publishing.</p><Button className="mt-4" onClick={() => navigate("/jobs/recruiter/create")}><Plus className="mr-1 size-4" />Create job</Button></div> :
      <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-3 font-medium">Listing</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Deadline</th><th className="px-4 py-3 font-medium">Created</th><th className="px-4 py-3 text-right font-medium">Actions</th></tr></thead><tbody className="divide-y divide-slate-100">{jobs.map(job => <tr key={job.id} className="align-top hover:bg-slate-50/70"><td className="max-w-sm px-4 py-4"><p className="font-semibold text-slate-900">{job.title}</p><p className="mt-1 text-xs text-slate-500">{pretty(job.opportunity_type)} · {job.location}</p></td><td className="px-4 py-4"><Badge variant={job.lifecycle_status === "PUBLISHED" ? "default" : "outline"}>{lifecycleLabel[job.lifecycle_status] || pretty(job.lifecycle_status)}</Badge></td><td className="px-4 py-4 whitespace-nowrap text-slate-600">{job.application_deadline || "—"}</td><td className="px-4 py-4 whitespace-nowrap text-slate-600">{job.created_at ? new Date(job.created_at).toLocaleDateString() : "—"}</td><td className="px-4 py-4"><div className="flex justify-end gap-1">{job.lifecycle_status !== "ARCHIVED" && job.lifecycle_status !== "CLOSED" && <Button size="sm" variant="outline" onClick={() => navigate(`/jobs/recruiter/${encodeURIComponent(job.id)}/edit`)}>Edit</Button>}{(lifecycle[job.lifecycle_status] || []).map(action => <Button key={action} size="sm" variant={action === "publish" || action === "resume" || action === "reopen" ? "default" : "outline"} disabled={busy === job.id + action} onClick={() => void jobAction(job, action)}>{busy === job.id + action ? <LoaderCircle className="size-3.5 animate-spin" /> : pretty(action)}</Button>)}</div></td></tr>)}</tbody></table></div>}
      <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3"><span className="text-xs text-slate-500">Page size 20</span><div className="flex gap-2"><Button size="sm" variant="outline" disabled={offset === 0 || jobsLoading} onClick={() => setOffset(Math.max(0, offset - 20))}><ChevronLeft className="size-4" />Previous</Button><Button size="sm" variant="outline" disabled={!hasMore || jobsLoading} onClick={() => setOffset(offset + 20)}>Next<ChevronRight className="size-4" /></Button></div></div>
    </section>}
    {!orgLoading && orgId && (section === "create" || section === "edit") && <section className="rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
      {formLoading ? <div className="h-64 animate-pulse rounded-lg bg-slate-100" /> : <form className="space-y-6" onSubmit={event => void saveJob(event, false)}>
        <div className="grid gap-4 md:grid-cols-2"><Field label="Job title *"><Input required minLength={2} maxLength={255} value={form.title} onChange={e => updateField("title", e.target.value)} /></Field><Field label="Location *"><Input required minLength={2} maxLength={150} value={form.location} onChange={e => updateField("location", e.target.value)} placeholder="City, country or Remote" /></Field>
        <Field label="Opportunity type *"><select className={fieldClass} value={form.opportunity_type} onChange={e => { updateField("opportunity_type", e.target.value); updateField("employment_type", e.target.value === "INTERNSHIP" ? "INTERNSHIP" : form.employment_type === "INTERNSHIP" ? "FULL_TIME" : form.employment_type); }}><option value="JOB">Job</option><option value="INTERNSHIP">Internship</option></select></Field>
        <Field label="Employment type *"><select className={fieldClass} value={form.employment_type} onChange={e => updateField("employment_type", e.target.value)}><option value="FULL_TIME">Full-time</option><option value="PART_TIME">Part-time</option><option value="INTERNSHIP">Internship</option><option value="CONTRACT">Contract</option><option value="TEMPORARY">Temporary</option></select></Field>
        <Field label="Workplace arrangement *"><select className={fieldClass} value={form.work_mode} onChange={e => updateField("work_mode", e.target.value)}><option value="ONSITE">On-site</option><option value="HYBRID">Hybrid</option><option value="REMOTE">Remote</option></select></Field><Field label="Department"><Input value={form.department} maxLength={120} onChange={e => updateField("department", e.target.value)} /></Field>
        <Field label="Application deadline *"><Input required type="date" min={new Date().toISOString().slice(0,10)} value={form.application_deadline} onChange={e => updateField("application_deadline", e.target.value)} /></Field><Field label="Number of openings"><Input required type="number" min="1" max="100000" value={form.openings} onChange={e => updateField("openings", e.target.value)} /></Field>
        <Field label="Summary"><Input maxLength={500} value={form.summary} onChange={e => updateField("summary", e.target.value)} /></Field><Field label="Education requirements"><Input maxLength={2000} value={form.education_requirements} onChange={e => updateField("education_requirements", e.target.value)} /></Field>
        <Field label="Minimum experience (years)"><Input type="number" min="0" max="60" step="0.5" value={form.experience_min_years} onChange={e => updateField("experience_min_years", e.target.value)} /></Field><Field label="Maximum experience (years)"><Input type="number" min="0" max="60" step="0.5" value={form.experience_max_years} onChange={e => updateField("experience_max_years", e.target.value)} /></Field>
        <Field label="Compensation minimum"><Input type="number" min="0" step="0.01" value={form.compensation_min} onChange={e => updateField("compensation_min", e.target.value)} /></Field><Field label="Compensation maximum"><Input type="number" min="0" step="0.01" value={form.compensation_max} onChange={e => updateField("compensation_max", e.target.value)} /></Field>
        <Field label="Currency"><Input required minLength={3} maxLength={3} value={form.compensation_currency} onChange={e => updateField("compensation_currency", e.target.value.toUpperCase())} /></Field><Field label="Compensation period"><select className={fieldClass} value={form.compensation_period} onChange={e => updateField("compensation_period", e.target.value)}><option value="YEAR">Per year</option><option value="MONTH">Per month</option><option value="HOUR">Per hour</option><option value="ONE_TIME">One-time</option></select></Field>
        <Field label="Start date"><Input type="date" value={form.starts_on} onChange={e => updateField("starts_on", e.target.value)} /></Field><Field label="End date"><Input type="date" value={form.ends_on} min={form.starts_on || undefined} onChange={e => updateField("ends_on", e.target.value)} /></Field>
        <Field label="Required skills" hint="Comma-separated skills"><Input value={form.required_skills} onChange={e => updateField("required_skills", e.target.value)} /></Field><Field label="Preferred skills" hint="Comma-separated skills"><Input value={form.preferred_skills} onChange={e => updateField("preferred_skills", e.target.value)} /></Field>
        <div className="md:col-span-2"><Field label="External application URL" hint="Optional. Must be a valid HTTP(S) URL."><Input type="url" value={form.public_application_url} onChange={e => updateField("public_application_url", e.target.value)} placeholder="https://…" /></Field></div>
        <div className="md:col-span-2"><Field label="Full description *" hint="At least 20 characters."><Textarea required minLength={20} maxLength={30000} rows={9} className="min-h-48 w-full resize-y" value={form.description} onChange={e => updateField("description", e.target.value)} /></Field></div>
        <div className="flex items-center gap-2"><input id="comp-visible" type="checkbox" checked={form.compensation_visible} onChange={e => updateField("compensation_visible", e.target.checked)} className="size-4 accent-teal-700" /><label htmlFor="comp-visible" className="text-sm text-slate-700">Show compensation in the public listing</label></div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4"><p className="text-xs text-slate-500">{dirty ? "Unsaved changes" : "All changes saved"} · New listings are created as drafts.</p><div className="flex gap-2"><Button type="button" variant="outline" onClick={() => { if (!dirty || window.confirm("Discard unsaved changes?")) navigate("/jobs/recruiter"); }}>Cancel</Button><Button type="submit" disabled={busy !== "" || formLoading || !dirty}><Save className="mr-1 size-4" />{busy === "save" ? "Saving…" : "Save draft"}</Button><Button type="button" disabled={busy !== "" || formLoading} onClick={event => { const formElement = event.currentTarget.form; if (formElement?.reportValidity()) void saveJob({ preventDefault: () => {}, currentTarget: formElement } as unknown as FormEvent, true); }}><Send className="mr-1 size-4" />Save & publish</Button></div></div>
      </form>}
    </section>}
    {!orgLoading && orgId && section === "applications" && <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row"><select aria-label="Filter by stage" className={fieldClass + " sm:max-w-56"} value={stageFilter} onChange={e => { setStageFilter(e.target.value); setOffset(0); }}><option value="">All stages</option>{stages.map(stage => <option key={stage} value={stage}>{pretty(stage)}</option>)}</select><select aria-label="Filter by job" className={fieldClass + " sm:max-w-md"} value={jobFilter} onChange={e => { setJobFilter(e.target.value); setOffset(0); }}><option value="">All listings</option>{jobs.map(job => <option key={job.id} value={job.id}>{job.title}</option>)}</select><Button variant="outline" onClick={() => void loadApplications()} disabled={appLoading}><RefreshCw className={"mr-1 size-4 " + (appLoading ? "animate-spin" : "")} />Refresh</Button></div>
      {appLoading ? <div className="space-y-3 p-4">{[1,2,3].map(i => <div key={i} className="h-16 animate-pulse rounded bg-slate-100" />)}</div> : applicants.length === 0 ? <div className="p-12 text-center"><h2 className="font-semibold text-slate-900">No applications found</h2><p className="mt-1 text-sm text-slate-500">Try a different stage or listing filter.</p></div> : <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-4 py-3 font-medium">Applicant</th><th className="px-4 py-3 font-medium">Opportunity</th><th className="px-4 py-3 font-medium">Stage</th><th className="px-4 py-3 font-medium">Applied</th><th className="px-4 py-3"></th></tr></thead><tbody className="divide-y divide-slate-100">{applicants.map(item => <tr key={item.id}><td className="px-4 py-4"><p className="font-medium text-slate-900">{item.applicant_name}</p><p className="text-xs text-slate-500">{item.applicant_email}</p></td><td className="px-4 py-4 text-slate-700">{item.job_title}</td><td className="px-4 py-4"><Badge variant="outline">{pretty(item.stage)}</Badge></td><td className="px-4 py-4 text-slate-600">{item.applied_at ? new Date(item.applied_at).toLocaleDateString() : "—"}</td><td className="px-4 py-4 text-right"><Button size="sm" variant="outline" onClick={() => navigate(`/jobs/recruiter/applications/${encodeURIComponent(item.id)}`)}>Review</Button></td></tr>)}</tbody></table></div>}
      <div className="flex justify-end gap-2 border-t border-slate-200 p-3"><Button size="sm" variant="outline" disabled={offset === 0 || appLoading} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous</Button><Button size="sm" variant="outline" disabled={!hasMore || appLoading} onClick={() => setOffset(offset + 25)}>Next</Button></div>
    </section>}
    {!orgLoading && orgId && section === "application-detail" && <section className="grid gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
      {detail ? <><div className="space-y-5 rounded-xl border border-slate-200 bg-white p-5"><div><p className="text-xs uppercase tracking-wide text-slate-500">Applicant</p><h2 className="mt-1 text-xl font-semibold">{detail.applicant?.name || "Applicant"}</h2><p className="text-sm text-slate-600">{detail.applicant?.email || ""}</p><p className="mt-3 text-sm text-slate-700">Applied for <strong>{detail.job_title}</strong></p><Badge className="mt-2" variant="outline">{pretty(detail.stage)}</Badge></div><form onSubmit={event => void changeStage(event)} className="space-y-3 border-t border-slate-100 pt-4"><Field label="Move to stage"><select className={fieldClass} value={newStage} onChange={e => setNewStage(e.target.value)}><option value={detail.stage}>{pretty(detail.stage)} (current)</option>{(transitions[detail.stage] || []).map(stage => <option key={stage} value={stage}>{pretty(stage)}</option>)}</select></Field><Field label="Internal stage note (optional)"><Textarea rows={2} maxLength={2000} value={stageNote} onChange={e => setStageNote(e.target.value)} placeholder="Reason or context for the transition" /></Field><Button type="submit" disabled={busy !== "" || newStage === detail.stage}><Check className="mr-1 size-4" />Update stage</Button><p className="text-xs text-slate-500">Hiring decisions do not create an academic placement. Kairos placement workflows remain separate.</p></form><div className="border-t border-slate-100 pt-4"><h3 className="font-semibold">Stage history</h3>{detail.stage_history.length ? <ol className="mt-3 space-y-3">{detail.stage_history.map((event, i) => <li key={i} className="border-l-2 border-slate-200 pl-3"><p className="text-sm font-medium">{pretty(event.from_stage)} → {pretty(event.to_stage)}</p><p className="text-xs text-slate-500">{new Date(event.created_at).toLocaleString()}</p>{event.note && <p className="mt-1 text-sm text-slate-600">{event.note}</p>}</li>)}</ol> : <p className="mt-2 text-sm text-slate-500">No stage changes recorded.</p>}</div></div>
      <div className="rounded-xl border border-slate-200 bg-white p-5"><h3 className="font-semibold">Private recruiter notes</h3><p className="mt-1 text-xs text-slate-500">Visible to authorized members of this employer organization.</p><form onSubmit={event => void addNote(event)} className="mt-4 space-y-2"><Textarea required minLength={1} maxLength={5000} rows={3} value={noteText} onChange={e => setNoteText(e.target.value)} placeholder="Add a private note…" /><Button type="submit" size="sm" disabled={!noteText.trim() || busy !== ""}>{busy === "note" ? "Saving…" : "Add note"}</Button></form><div className="mt-5 space-y-3">{notes.map(note => <article key={note.id} className="rounded-lg bg-slate-50 p-3"><p className="whitespace-pre-wrap text-sm text-slate-700">{note.body}</p><p className="mt-2 text-xs text-slate-500">{new Date(note.created_at).toLocaleString()}</p></article>)}{!notes.length && <p className="text-sm text-slate-500">No private notes yet.</p>}</div></div></> : <div className="rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-500">Loading applicant details…</div>}
    </section>}
  </main>;
}
