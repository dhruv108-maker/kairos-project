import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { Activity, AlertCircle, ArrowUpRight, BookOpen, BriefcaseBusiness, CheckCircle2, Clock3, FileText, MessageSquareText, RefreshCw, Send, Upload } from "lucide-react";
import { apiRequest, ApiError } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

type Placement = { id: string; application_id: string; student_id: number; faculty_supervisor_id: string | null; start_date: string; end_date: string; status: string };
type Application = { id: string; status: string; applied_at?: string | null; opportunity?: { id: string; title: string; company_name?: string | null; starts_on?: string | null; ends_on?: string | null; location?: string | null } };
type Report = { id: string; placement_id: string; requirement_id?: string | null; title: string; latest_version_number: number; status: string; review_feedback?: string | null; reviewed_by_account_id?: string | null; reviewed_at?: string | null; created_at?: string; updated_at?: string };
type WorkLog = { id: string; placement_id: string; work_date: string; summary: string; tasks_completed: string; skills_used?: string | null; challenges?: string | null; learning_outcomes?: string | null; next_steps?: string | null; status: string; created_at?: string; updated_at?: string; latest_review?: { decision: string; feedback: string; reviewer_role: string; created_at?: string } | null };
type ReportVersion = { id: string; submission_id: string; version_number: number; file_id: string; submission_notes?: string | null; submitted_at?: string };
type Requirement = { id: string; title: string; description?: string | null; due_date?: string | null; is_required: boolean; is_active: boolean; submission_status?: string | null };
type UploadResult = { id: string; original_name: string; file_size_bytes: number; mime_type: string; created_at?: string };
type AsyncState<T> = { loading: boolean; value: T | null; error: string | null };
type View = "overview" | "reports" | "feedback" | "activity";
const emptyState = <T,>(): AsyncState<T> => ({ loading: true, value: null, error: null });
const formatDate = (value?: string | null) => { if (!value) return "Not recorded"; const d = new Date(value); return Number.isNaN(d.getTime()) ? "Not recorded" : d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }); };
const formatDateTime = (value?: string | null) => { if (!value) return "Not recorded"; const d = new Date(value); return Number.isNaN(d.getTime()) ? "Not recorded" : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); };
const prettyStatus = (value?: string | null) => (value || "UNKNOWN").toLowerCase().replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
const editable = (status: string) => ["DRAFT", "REVISION_REQUIRED"].includes(status);
const errorMessage = (error: unknown) => { if (error instanceof ApiError) { if (error.status === 401) return "Your session expired. Please sign in again."; if (error.status === 403) return "Your account is not authorized for this action."; if (error.status === 404) return "The requested record was not found or is not available to your account."; if (error.status === 409) return "The record changed or this action is not valid in its current state. Refresh and retry."; if (error.status === 422) return error.message; return error.message; } return "Kairos could not be reached. Check your connection and try again."; };
const statusVariant = (v: string): "default" | "secondary" | "outline" | "destructive" => ["APPROVED", "COMPLETED", "ONGOING"].includes(v) ? "default" : ["REJECTED", "TERMINATED"].includes(v) ? "destructive" : ["SUBMITTED", "UNDER_EVALUATION", "OFFERED"].includes(v) ? "secondary" : "outline";
function PageHeading({ title, description }: { title: string; description: string }) { return <div className="mb-6"><p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-teal-700"><BriefcaseBusiness className="size-4" /> During internship</p><h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{description}</p></div>; }
function StateNotice({ title, message, onRetry }: { title: string; message: string; onRetry?: () => void }) { return <Alert variant="destructive"><AlertCircle className="size-4" /><AlertTitle>{title}</AlertTitle><AlertDescription><div className="flex flex-wrap items-center justify-between gap-3"><span>{message}</span>{onRetry && <Button variant="outline" size="sm" onClick={onRetry}><RefreshCw className="mr-2 size-3.5" />Retry</Button>}</div></AlertDescription></Alert>; }
function StatusBadge({ status }: { status: string }) { return <Badge variant={statusVariant(status)}>{prettyStatus(status)}</Badge>; }

export default function DuringInternshipPage() {
  const { account } = useAuth();
  const roles = useMemo(() => (account?.roles || []).map((r) => r.toUpperCase()), [account]);
  const isStudent = roles.includes("STUDENT");
  const isFaculty = roles.includes("FACULTY");
  const [view, setView] = useState<View>("overview");
  const [reloadKey, setReloadKey] = useState(0);
  const [applications, setApplications] = useState<AsyncState<Application[]>>(emptyState());
  const [reports, setReports] = useState<AsyncState<Report[]>>(emptyState());
  const [placements, setPlacements] = useState<AsyncState<Placement[]>>(emptyState());
  const [requirements, setRequirements] = useState<AsyncState<Array<{ requirement: Requirement; submission_status?: string | null }>>>(emptyState());
  const [workLogs, setWorkLogs] = useState<AsyncState<WorkLog[]>>(emptyState());
  const [logPlacementId, setLogPlacementId] = useState("");
  const [logDate, setLogDate] = useState(new Date().toISOString().slice(0, 10));
  const [logSummary, setLogSummary] = useState("");
  const [logTasks, setLogTasks] = useState("");
  const [logSkills, setLogSkills] = useState("");
  const [logChallenges, setLogChallenges] = useState("");
  const [logLearning, setLogLearning] = useState("");
  const [logNext, setLogNext] = useState("");
  const [editingLogId, setEditingLogId] = useState("");
  const [logBusy, setLogBusy] = useState(false);
  const [supervisedLogs, setSupervisedLogs] = useState<AsyncState<WorkLog[]>>(emptyState());
  const [reviewText, setReviewText] = useState<Record<string, string>>({});
  const [reviewDecision, setReviewDecision] = useState<Record<string, "ACKNOWLEDGED" | "REVISION_REQUIRED">>({});
  const [selectedReport, setSelectedReport] = useState("");
  const [versions, setVersions] = useState<ReportVersion[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [versionError, setVersionError] = useState<string | null>(null);
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const [reviewBusy, setReviewBusy] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftNotes, setDraftNotes] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [reportBusy, setReportBusy] = useState(false);

  const load = useCallback(async () => {
    if (isStudent) {
      setApplications(emptyState()); setReports(emptyState()); setRequirements(emptyState());
      await Promise.all([
        apiRequest<{ items: Application[] }>("/modules/internships/applications/me").then((r) => setApplications({ loading: false, value: r.items || [], error: null })).catch((e) => setApplications({ loading: false, value: null, error: errorMessage(e) })),
        apiRequest<{ items: Report[] }>("/reports/me").then((r) => setReports({ loading: false, value: r.items || [], error: null })).catch((e) => setReports({ loading: false, value: null, error: errorMessage(e) })),
        apiRequest<{ items: Array<{ requirement: Requirement; submission_status?: string | null }> }>("/reports/requirements/me").then((r) => setRequirements({ loading: false, value: r.items || [], error: null })).catch((e) => setRequirements({ loading: false, value: null, error: errorMessage(e) })),
      ]);
    } else if (isFaculty) {
      setReports(emptyState()); setPlacements(emptyState());
      await Promise.all([
        apiRequest<{ items: Report[] }>("/reports/faculty/me").then((r) => setReports({ loading: false, value: r.items || [], error: null })).catch((e) => setReports({ loading: false, value: null, error: errorMessage(e) })),
        apiRequest<{ items: Placement[] }>("/modules/internships/placements/supervised").then((r) => setPlacements({ loading: false, value: r.items || [], error: null })).catch((e) => setPlacements({ loading: false, value: null, error: errorMessage(e) })),
      ]);
    } else {
      setApplications({ loading: false, value: [], error: null }); setReports({ loading: false, value: [], error: null }); setRequirements({ loading: false, value: [], error: null });
      setPlacements({ loading: false, value: [], error: "Assigned industry-mentor endpoints are not implemented in this branch." });
    }
  }, [isStudent, isFaculty]);
  const loadLogs = useCallback(async () => {
    if (isStudent) {
      setWorkLogs(emptyState());
      try {
        const r = await apiRequest<{ items: WorkLog[] }>("/modules/internships/work-logs/me");
        setWorkLogs({ loading: false, value: r.items || [], error: null });
        const p = await apiRequest<{ items: Placement[] }>("/modules/internships/placements/me");
        setPlacements((old) => old.value === null ? { loading: false, value: p.items || [], error: null } : old);
        if (!logPlacementId && p.items?.length) setLogPlacementId(p.items.find((x) => x.status === "ONGOING")?.id || "");
      } catch (e) { setWorkLogs({ loading: false, value: null, error: errorMessage(e) }); }
    } else if (isFaculty) {
      setSupervisedLogs(emptyState());
      try {
        const r = await apiRequest<{ items: WorkLog[] }>("/modules/internships/work-logs/supervised");
        setSupervisedLogs({ loading: false, value: r.items || [], error: null });
      } catch (e) { setSupervisedLogs({ loading: false, value: null, error: errorMessage(e) }); }
    }
  }, [isStudent, isFaculty, logPlacementId]);
  useEffect(() => { void loadLogs(); }, [loadLogs, reloadKey]);

  const clearLogForm = () => {
    setEditingLogId(""); setLogDate(new Date().toISOString().slice(0, 10)); setLogSummary("");
    setLogTasks(""); setLogSkills(""); setLogChallenges(""); setLogLearning(""); setLogNext("");
  };
  const saveLog = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!logPlacementId || !logSummary.trim() || !logTasks.trim()) { toast.error("Choose an ongoing placement and complete the summary and tasks."); return; }
    setLogBusy(true);
    const payload = { placement_id: logPlacementId, work_date: logDate, summary: logSummary.trim(),
      tasks_completed: logTasks.trim(), skills_used: logSkills.trim() || null, challenges: logChallenges.trim() || null,
      learning_outcomes: logLearning.trim() || null, next_steps: logNext.trim() || null, status: "DRAFT" };
    try {
      const saved = await apiRequest<WorkLog>(editingLogId ? `/modules/internships/work-logs/${encodeURIComponent(editingLogId)}` : "/modules/internships/work-logs", {
        method: editingLogId ? "PATCH" : "POST", body: JSON.stringify(payload)
      });
      toast.success(`Work-log ${prettyStatus(saved.status)} saved.`);
      clearLogForm(); setReloadKey((n) => n + 1);
    } catch (e) { toast.error(errorMessage(e)); } finally { setLogBusy(false); }
  };
  const editLog = (log: WorkLog) => {
    setEditingLogId(log.id); setLogPlacementId(log.placement_id); setLogDate(log.work_date);
    setLogSummary(log.summary); setLogTasks(log.tasks_completed); setLogSkills(log.skills_used || "");
    setLogChallenges(log.challenges || ""); setLogLearning(log.learning_outcomes || ""); setLogNext(log.next_steps || "");
    setView("activity");
  };
  const submitLog = async (logId: string) => {
    setLogBusy(true);
    try { const saved = await apiRequest<WorkLog>(`/modules/internships/work-logs/${encodeURIComponent(logId)}/submit`, { method: "POST" }); toast.success(`Work log ${prettyStatus(saved.status)}.`); setReloadKey((n) => n + 1); }
    catch (e) { toast.error(errorMessage(e)); } finally { setLogBusy(false); }
  };
  const reviewLog = async (logId: string) => {
    const decision = reviewDecision[logId] || "ACKNOWLEDGED";
    if (!reviewText[logId]?.trim()) { toast.error("Feedback is required for a work-log review."); return; }
    setLogBusy(true);
    try { const result = await apiRequest<{ work_log: WorkLog }>(`/modules/internships/work-logs/${encodeURIComponent(logId)}/review`, { method: "POST", body: JSON.stringify({ decision, feedback: reviewText[logId].trim() }) }); toast.success(`Work log ${prettyStatus(result.work_log.status)}.`); setReloadKey((n) => n + 1); }
    catch (e) { toast.error(errorMessage(e)); } finally { setLogBusy(false); }
  };

  useEffect(() => { void load(); }, [load, reloadKey]);

  const openVersions = useCallback(async (reportId: string) => {
    setSelectedReport(reportId); setVersions([]); setVersionError(null); setVersionsLoading(true);
    try { const r = await apiRequest<{ items: ReportVersion[] }>(`/reports/${encodeURIComponent(reportId)}/versions`); setVersions(r.items || []); }
    catch (e) { setVersionError(errorMessage(e)); } finally { setVersionsLoading(false); }
  }, []);
  const submitReport = async (reportId: string) => { setReportBusy(true); try { const r = await apiRequest<Report>(`/reports/${encodeURIComponent(reportId)}/submit`, { method: "POST" }); toast.success(`Report status: ${prettyStatus(r.status)}`); setReloadKey((n) => n + 1); } catch (e) { toast.error(errorMessage(e)); } finally { setReportBusy(false); } };
  const uploadRevision = async (reportId: string, file: File) => { setReportBusy(true); try { const body = new FormData(); body.append("file", file); const stored = await apiRequest<UploadResult>("/storage/upload", { method: "POST", body }); await apiRequest(`/reports/${encodeURIComponent(reportId)}/versions`, { method: "POST", body: JSON.stringify({ file_id: stored.id, submission_notes: "Resubmitted revision" }) }); toast.success("New report version saved."); setReloadKey((n) => n + 1); await openVersions(reportId); } catch (e) { toast.error(errorMessage(e)); } finally { setReportBusy(false); } };
  const createReport = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedFile || !draftTitle.trim()) return;
    setReportBusy(true);
    try {
      const placementResponse = await apiRequest<{ items: Array<{ id: string; status: string }> }>("/modules/internships/placements/me");
      const placement = (placementResponse.items || []).find((p) => p.status === "ONGOING");
      if (!placement) { toast.error("No ongoing persisted placement is linked to your account."); return; }
      const body = new FormData(); body.append("file", selectedFile);
      const stored = await apiRequest<UploadResult>("/storage/upload", { method: "POST", body });
      const report = await apiRequest<Report>("/reports", { method: "POST", body: JSON.stringify({ placement_id: placement.id, title: draftTitle.trim(), file_id: stored.id, submission_notes: draftNotes.trim() || null }) });
      toast.success("Draft report created in Kairos.");
      setDraftTitle(""); setDraftNotes(""); setSelectedFile(null); setSelectedReport(report.id); setView("reports"); setReloadKey((n) => n + 1); await openVersions(report.id);
    } catch (e) { toast.error(errorMessage(e)); }
    finally { setReportBusy(false); }
  };
  const reviewReport = async (reportId: string, status: string) => {
    if (status === "REVISION_REQUIRED" && !reviewNotes[reportId]?.trim()) { toast.error("Feedback is required when requesting a revision."); return; }
    setReviewBusy(reportId); try { const r = await apiRequest<Report>(`/reports/${encodeURIComponent(reportId)}/status`, { method: "PATCH", body: JSON.stringify({ status, feedback_comments: reviewNotes[reportId]?.trim() || null }) }); toast.success(`Report status updated to ${prettyStatus(r.status)}.`); setReloadKey((n) => n + 1); } catch (e) { toast.error(errorMessage(e)); } finally { setReviewBusy(null); }
  };
  const errors = [applications.error, reports.error, placements.error, requirements.error].filter((v): v is string => Boolean(v));
  const loading = (isStudent && applications.loading) || reports.loading || (isFaculty && placements.loading);
  const pending = (reports.value || []).filter((r) => ["SUBMITTED", "UNDER_EVALUATION"].includes(r.status));
  const selectedReportItem = (reports.value || []).find((r) => r.id === selectedReport);
  const timeline = [
    { title: "Placement", done: (placements.value || []).some((p) => p.status === "ONGOING"), detail: isStudent ? "Uses saved placement records, not application status." : "Uses the faculty-scoped placement endpoint." },
    { title: "Work logs", done: false, detail: "No work-log model or endpoint exists in this branch." },
    { title: "Reports", done: (reports.value || []).some((r) => r.status === "APPROVED"), detail: `${reports.value?.length ?? 0} report submission(s) returned by Kairos.` },
    { title: "Evaluation", done: false, detail: "Griffin evaluation is tracked separately and requires assigned faculty authorization." },
  ];

  return <div className="pb-8">
    <PageHeading title={isStudent ? "My internship" : isFaculty ? "Internship supervision" : "During internship"} description={isStudent ? "Keep your placement, report submissions, requirements, and feedback in one workspace." : isFaculty ? "Review reports and inspect only placements returned by the faculty supervision API." : "This workspace only exposes workflows supported by your current Kairos permissions and backend contracts."} />
    <div className="mb-6 flex flex-wrap gap-2 border-b pb-3">{([[ "overview", "Overview", Activity ], ["reports", "Reports", FileText], ["feedback", "Feedback", MessageSquareText], ["activity", isStudent ? "Work logs" : "Supervision", Clock3]] as const).map(([key, label, Icon]) => <Button key={key} variant={view === key ? "default" : "outline"} size="sm" onClick={() => setView(key)}><Icon className="mr-2 size-4" />{label}</Button>)}<div className="ml-auto"><Button variant="ghost" size="sm" onClick={() => setReloadKey((n) => n + 1)}><RefreshCw className="mr-2 size-4" />Refresh</Button></div></div>
    {errors.length > 0 && <div className="mb-4 space-y-2">{errors.map((message, i) => <StateNotice key={`${message}-${i}`} title="Workspace data unavailable" message={message} onRetry={() => setReloadKey((n) => n + 1)} />)}</div>}
    {loading ? <div className="space-y-4"><Skeleton className="h-28 w-full" /><div className="grid gap-4 md:grid-cols-2"><Skeleton className="h-36" /><Skeleton className="h-36" /></div></div> : <>
      {view === "overview" && <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-3"><Card><CardHeader><CardDescription>{isStudent ? "Applications" : "Supervised placements"}</CardDescription><CardTitle className="text-2xl">{isStudent ? applications.value?.length ?? "—" : placements.value?.length ?? "—"}</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">{isStudent ? "Belonging to your authenticated account." : "From role-scoped supervision records."}</CardContent></Card><Card><CardHeader><CardDescription>Reports</CardDescription><CardTitle className="text-2xl">{reports.value?.length ?? "—"}</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">{pending.length} submitted or under evaluation</CardContent></Card><Card><CardHeader><CardDescription>Work logs</CardDescription><CardTitle className="text-2xl">Unavailable</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">The backend currently has no persisted work-log contract.</CardContent></Card></div>
        <Card><CardHeader><CardTitle>Internship journey</CardTitle><CardDescription>Progress derives from persisted records, not page visits.</CardDescription></CardHeader><CardContent><div className="space-y-5">{timeline.map((item, i) => <div key={item.title} className="flex gap-3"><div className={`mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full border ${item.done ? "border-teal-600 bg-teal-50 text-teal-700" : "border-border text-muted-foreground"}`}>{item.done ? <CheckCircle2 className="size-4" /> : <span className="text-xs font-semibold">{i + 1}</span>}</div><div><div className="flex flex-wrap items-center gap-2"><p className="font-medium">{item.title}</p><Badge variant={item.done ? "default" : "outline"}>{item.done ? "Recorded" : "Pending / unsupported"}</Badge></div><p className="mt-1 text-sm text-muted-foreground">{item.detail}</p></div></div>)}</div></CardContent></Card>
        {isStudent && requirements.value && requirements.value.length > 0 && <Card><CardHeader><CardTitle>Report requirements</CardTitle><CardDescription>Active requirements returned for your institution.</CardDescription></CardHeader><CardContent><div className="divide-y">{requirements.value.map(({ requirement: r, submission_status }) => <div key={r.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-medium">{r.title}</p>{r.description && <p className="text-sm text-muted-foreground">{r.description}</p>}<p className="mt-1 text-xs text-muted-foreground">Due {formatDate(r.due_date)} · {r.is_required ? "Required" : "Optional"}</p></div><Badge variant="outline">{prettyStatus(submission_status || "NOT_STARTED")}</Badge></div>)}</div></CardContent></Card>}
        <Card><CardHeader><CardTitle>{isStudent ? "My applications" : "Supervised placements"}</CardTitle><CardDescription>Recruitment status is distinct from placement status.</CardDescription></CardHeader><CardContent>{isStudent && applications.value?.length ? <Table><TableHeader><TableRow><TableHead>Opportunity</TableHead><TableHead>Organization</TableHead><TableHead>Application status</TableHead><TableHead>Applied</TableHead></TableRow></TableHeader><TableBody>{applications.value.map((a) => <TableRow key={a.id}><TableCell className="whitespace-normal font-medium">{a.opportunity?.title || "Opportunity unavailable"}</TableCell><TableCell>{a.opportunity?.company_name || "Not recorded"}</TableCell><TableCell><StatusBadge status={a.status} /></TableCell><TableCell>{formatDate(a.applied_at)}</TableCell></TableRow>)}</TableBody></Table> : isFaculty && placements.value?.length ? <div className="divide-y">{placements.value.map((p) => <div key={p.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-medium">Placement {p.id}</p><p className="text-sm text-muted-foreground">{formatDate(p.start_date)} – {formatDate(p.end_date)}</p></div><StatusBadge status={p.status} /></div>)}</div> : <div className="py-8 text-center text-sm text-muted-foreground">{isStudent ? "No applications returned for this account." : isFaculty ? "No supervised placements returned." : "Assigned industry-mentor endpoints are not implemented in this branch."}</div>}<div className="mt-4"><Button asChild variant="outline" size="sm"><Link to="/jobs"><BriefcaseBusiness className="mr-2 size-4" />Explore jobs & internships<ArrowUpRight className="ml-2 size-4" /></Link></Button></div></CardContent></Card>
      </div>}
      {view === "reports" && <div className="space-y-6">
        {isStudent && <Card><CardHeader><CardTitle>New report draft</CardTitle><CardDescription>Upload through Kairos private storage and attach the file to a verified ongoing placement.</CardDescription></CardHeader><CardContent><form className="grid gap-4" onSubmit={createReport}><div className="grid gap-2"><Label htmlFor="report-title">Report title</Label><Input id="report-title" value={draftTitle} onChange={(e) => setDraftTitle(e.target.value)} maxLength={255} required placeholder="e.g. Weekly internship report" /></div><div className="grid gap-2"><Label htmlFor="report-notes">Submission notes (optional)</Label><Textarea id="report-notes" value={draftNotes} onChange={(e) => setDraftNotes(e.target.value)} maxLength={5000} placeholder="Summarize the submission." /></div><div className="grid gap-2"><Label htmlFor="report-file">Report file</Label><Input id="report-file" type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" onChange={(e) => setSelectedFile(e.target.files?.[0] || null)} required /></div><div><Button type="submit" disabled={reportBusy || !selectedFile || !draftTitle.trim()}><Upload className="mr-2 size-4" />{reportBusy ? "Saving…" : "Create draft report"}</Button></div></form></CardContent></Card>}
        <Card><CardHeader><CardTitle>{isFaculty ? "Reports for review" : "Report submissions"}</CardTitle><CardDescription>Review states and immutable versions from the existing report workflow.</CardDescription></CardHeader><CardContent>{reports.value?.length ? <div className="space-y-4">{reports.value.map((r) => <div key={r.id} className="rounded-lg border p-4"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0"><h3 className="font-medium">{r.title}</h3><p className="mt-1 text-xs text-muted-foreground">Version {r.latest_version_number} · Updated {formatDateTime(r.updated_at)}</p><p className="mt-1 text-xs text-muted-foreground">Placement {r.placement_id}</p></div><StatusBadge status={r.status} /></div>{r.review_feedback && <Alert className="mt-3"><MessageSquareText className="size-4" /><AlertTitle>Reviewer feedback</AlertTitle><AlertDescription>{r.review_feedback}</AlertDescription></Alert>}<div className="mt-4 flex flex-wrap gap-2"><Button variant="outline" size="sm" onClick={() => void openVersions(r.id)}><FileText className="mr-2 size-4" />Version history</Button>{isStudent && editable(r.status) && <><Button size="sm" disabled={reportBusy} onClick={() => void submitReport(r.id)}><Send className="mr-2 size-4" />Submit report</Button><label className="inline-flex cursor-pointer items-center rounded-lg border px-3 py-1.5 text-sm hover:bg-muted"><Upload className="mr-2 size-4" />Upload revision<input type="file" className="sr-only" accept=".pdf,.png,.jpg,.jpeg,.txt" disabled={reportBusy} onChange={(e) => { const f = e.target.files?.[0]; if (f) void uploadRevision(r.id, f); e.currentTarget.value = ""; }} /></label></>}{isFaculty && ["SUBMITTED", "UNDER_EVALUATION"].includes(r.status) && <div className="mt-2 w-full space-y-3 rounded-md bg-muted/40 p-3"><Label htmlFor={`review-notes-${r.id}`}>Review feedback</Label><Textarea id={`review-notes-${r.id}`} value={reviewNotes[r.id] || ""} onChange={(e) => setReviewNotes((old) => ({ ...old, [r.id]: e.target.value }))} placeholder="Required when requesting a revision" maxLength={5000} /><div className="flex flex-wrap gap-2">{(["UNDER_EVALUATION", "REVISION_REQUIRED", "APPROVED", "REJECTED"] as const).filter((s) => s !== r.status).map((s) => <Button key={s} size="sm" variant={s === "APPROVED" ? "default" : "outline"} disabled={reviewBusy === r.id} onClick={() => void reviewReport(r.id, s)}>{reviewBusy === r.id ? "Saving…" : prettyStatus(s)}</Button>)}</div></div>}</div></div>)}</div> : !reports.error ? <div className="py-10 text-center"><FileText className="mx-auto mb-2 size-7 text-muted-foreground" /><p className="font-medium">No report submissions</p><p className="mt-1 text-sm text-muted-foreground">{isStudent ? "Create a draft once an ongoing placement exists." : "No reports returned by the faculty listing endpoint."}</p></div> : null}</CardContent></Card>
        {selectedReportItem && <Card><CardHeader><CardTitle>Version history · {selectedReportItem.title}</CardTitle><CardDescription>Private files are fetched through the authorized storage endpoint.</CardDescription></CardHeader><CardContent>{versionsLoading ? <Skeleton className="h-12 w-full" /> : versionError ? <StateNotice title="Could not load version history" message={versionError} onRetry={() => void openVersions(selectedReport)} /> : !versions.length ? <p className="text-sm text-muted-foreground">No versions returned.</p> : <div className="divide-y">{versions.map((v) => <div key={v.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-medium">Version {v.version_number}</p><p className="text-xs text-muted-foreground">{v.submission_notes || "No notes"} · {formatDateTime(v.submitted_at)}</p></div><Button variant="outline" size="sm" onClick={async () => { try { const response = await fetch(`/api/v1/storage/${encodeURIComponent(v.file_id)}`, { headers: { Authorization: `Bearer ${sessionStorage.getItem("kairos.access_token") || ""}` } }); if (!response.ok) throw new Error(`Download failed (${response.status})`); const url = URL.createObjectURL(await response.blob()); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `report-version-${v.version_number}`; anchor.click(); URL.revokeObjectURL(url); } catch (e) { toast.error(e instanceof Error ? e.message : "Download failed"); } }}><FileText className="mr-2 size-4" />Download version</Button></div>)}</div>}</CardContent></Card>}
      </div>}
      {view === "feedback" && <div className="space-y-4">{reports.value?.some((r) => r.review_feedback) ? reports.value.filter((r) => r.review_feedback).map((r) => <Card key={r.id}><CardHeader><CardTitle className="text-base">{r.title}</CardTitle><CardDescription>Report review · {formatDateTime(r.reviewed_at)} · {prettyStatus(r.status)}</CardDescription></CardHeader><CardContent><p className="whitespace-pre-wrap text-sm leading-6">{r.review_feedback}</p></CardContent></Card>) : <Card><CardContent className="py-10 text-center"><MessageSquareText className="mx-auto mb-2 size-7 text-muted-foreground" /><p className="font-medium">No report feedback recorded</p><p className="mt-1 text-sm text-muted-foreground">Industry and faculty feedback is shown only where persisted and authorized.</p></CardContent></Card>}</div>}
      {view === "activity" && <div className="space-y-5">
        {isStudent && <>
          {placements.error && <StateNotice title="Placements unavailable" message={placements.error} onRetry={() => setReloadKey((n) => n + 1)} />}
          {placements.value?.length ? <Card><CardHeader><CardTitle>Work log entry</CardTitle><CardDescription>Record your work against an ongoing persisted placement. Submitted logs are locked until reviewed.</CardDescription></CardHeader><CardContent><form className="grid gap-4" onSubmit={saveLog}>
            <div className="grid gap-2"><Label htmlFor="log-placement">Internship placement</Label><Select value={logPlacementId} onValueChange={setLogPlacementId}><SelectTrigger id="log-placement" className="w-full"><SelectValue placeholder="Choose ongoing placement" /></SelectTrigger><SelectContent>{placements.value.filter((p) => p.status === "ONGOING").map((p) => <SelectItem key={p.id} value={p.id}>Placement {p.id} · {formatDate(p.start_date)} – {formatDate(p.end_date)}</SelectItem>)}</SelectContent></Select></div>
            <div className="grid gap-2"><Label htmlFor="log-date">Work date</Label><Input id="log-date" type="date" required max={new Date().toISOString().slice(0, 10)} value={logDate} onChange={(e) => setLogDate(e.target.value)} /></div>
            <div className="grid gap-2"><Label htmlFor="log-summary">Summary</Label><Input id="log-summary" required minLength={3} maxLength={255} value={logSummary} onChange={(e) => setLogSummary(e.target.value)} placeholder="What did you work on?" /></div>
            <div className="grid gap-2"><Label htmlFor="log-tasks">Tasks completed</Label><Textarea id="log-tasks" required minLength={3} maxLength={10000} value={logTasks} onChange={(e) => setLogTasks(e.target.value)} placeholder="Describe work completed and results." /></div>
            <div className="grid gap-2"><Label htmlFor="log-skills">Skills / technologies used</Label><Input id="log-skills" value={logSkills} onChange={(e) => setLogSkills(e.target.value)} maxLength={5000} /></div>
            <div className="grid gap-2"><Label htmlFor="log-challenges">Challenges encountered</Label><Textarea id="log-challenges" value={logChallenges} onChange={(e) => setLogChallenges(e.target.value)} maxLength={5000} /></div>
            <div className="grid gap-2"><Label htmlFor="log-learning">Learning outcomes</Label><Textarea id="log-learning" value={logLearning} onChange={(e) => setLogLearning(e.target.value)} maxLength={5000} /></div>
            <div className="grid gap-2"><Label htmlFor="log-next">Next steps</Label><Textarea id="log-next" value={logNext} onChange={(e) => setLogNext(e.target.value)} maxLength={5000} /></div>
            <div className="flex flex-wrap gap-2"><Button type="submit" disabled={logBusy || !logPlacementId || !logSummary.trim() || !logTasks.trim()}>{logBusy ? "Saving…" : editingLogId ? "Save changes" : "Save draft"}</Button>{editingLogId && <Button type="button" variant="outline" onClick={clearLogForm}>Cancel edit</Button>}</div>
          </form></CardContent></Card> : <Alert><BookOpen className="size-4" /><AlertTitle>No ongoing placement found</AlertTitle><AlertDescription>Work logs are enabled only after a manager creates a persisted placement for an OFFERED application.</AlertDescription></Alert>}
          <Card><CardHeader><CardTitle>Work log history</CardTitle><CardDescription>Chronological entries with server-confirmed status and latest persisted review.</CardDescription></CardHeader><CardContent>{workLogs.loading ? <Skeleton className="h-24 w-full" /> : workLogs.error ? <StateNotice title="Could not load work logs" message={workLogs.error} onRetry={() => setReloadKey((n) => n + 1)} /> : workLogs.value?.length ? <div className="space-y-3">{workLogs.value.map((log) => <div key={log.id} className="rounded-lg border p-4"><div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div><p className="font-medium">{log.summary}</p><p className="mt-1 text-xs text-muted-foreground">{formatDate(log.work_date)} · Updated {formatDateTime(log.updated_at)}</p></div><StatusBadge status={log.status} /></div><p className="mt-3 whitespace-pre-wrap text-sm">{log.tasks_completed}</p>{log.skills_used && <p className="mt-2 text-sm text-muted-foreground">Skills: {log.skills_used}</p>}{log.latest_review && <Alert className="mt-3"><MessageSquareText className="size-4" /><AlertTitle>{prettyStatus(log.latest_review.decision)} · {log.latest_review.reviewer_role}</AlertTitle><AlertDescription><p className="whitespace-pre-wrap">{log.latest_review.feedback}</p><p className="mt-1 text-xs">Reviewed {formatDateTime(log.latest_review.created_at)}</p></AlertDescription></Alert>}<div className="mt-3 flex gap-2">{log.status === "DRAFT" && <><Button variant="outline" size="sm" disabled={logBusy} onClick={() => editLog(log)}>Edit draft</Button><Button size="sm" disabled={logBusy} onClick={() => void submitLog(log.id)}>Submit for review</Button></>}</div></div>)}</div> : <div className="py-8 text-center text-sm text-muted-foreground">No work logs recorded yet.</div>}</CardContent></Card>
        </>}
        {isFaculty && <><Alert><BookOpen className="size-4" /><AlertTitle>Assigned supervision only</AlertTitle><AlertDescription>Only work logs attached to placements explicitly assigned to your faculty profile are returned.</AlertDescription></Alert><Card><CardHeader><CardTitle>Submitted work logs</CardTitle><CardDescription>Review feedback is retained as an append-only history.</CardDescription></CardHeader><CardContent>{supervisedLogs.loading ? <Skeleton className="h-24 w-full" /> : supervisedLogs.error ? <StateNotice title="Could not load supervised logs" message={supervisedLogs.error} onRetry={() => setReloadKey((n) => n + 1)} /> : supervisedLogs.value?.length ? <div className="space-y-4">{supervisedLogs.value.map((log) => <div key={log.id} className="rounded-lg border p-4"><div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div><p className="font-medium">{log.summary}</p><p className="text-xs text-muted-foreground">{formatDate(log.work_date)} · Placement {log.placement_id}</p></div><StatusBadge status={log.status} /></div><p className="mt-3 whitespace-pre-wrap text-sm">{log.tasks_completed}</p>{log.status === "SUBMITTED" && <div className="mt-3 space-y-3"><Label htmlFor={`log-review-${log.id}`}>Faculty feedback</Label><Textarea id={`log-review-${log.id}`} maxLength={5000} value={reviewText[log.id] || ""} onChange={(e) => setReviewText((old) => ({ ...old, [log.id]: e.target.value }))} placeholder="Provide actionable academic feedback." /><div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => setReviewDecision((old) => ({ ...old, [log.id]: "ACKNOWLEDGED" }))} disabled={logBusy}>Acknowledge</Button><Button size="sm" variant="outline" onClick={() => setReviewDecision((old) => ({ ...old, [log.id]: "REVISION_REQUIRED" }))} disabled={logBusy}>Request revision</Button><Button size="sm" onClick={() => void reviewLog(log.id)} disabled={logBusy || !reviewText[log.id]?.trim()}>Submit review ({prettyStatus(reviewDecision[log.id] || "ACKNOWLEDGED")})</Button></div></div>}</div>)}</div> : <div className="py-8 text-center text-sm text-muted-foreground">No supervised work logs returned.</div>}</CardContent></Card></>}
        {!isStudent && !isFaculty && <Alert variant="destructive"><AlertCircle className="size-4" /><AlertTitle>Mentor assignment contract missing</AlertTitle><AlertDescription>Industry mentor accounts do not have a canonical placement assignment model in this branch; access is therefore not inferred from employer organization or URL identifiers.</AlertDescription></Alert>}
      </div>}
    </>}
    <Separator className="my-8" /><p className="text-xs text-muted-foreground">Kairos · authenticated workspace · server-confirmed states only</p>
  </div>;
}