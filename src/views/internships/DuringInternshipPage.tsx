import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  AlertCircle, ArrowDownToLine, BookOpen, BriefcaseBusiness, CalendarDays, Check,
  FileText, GraduationCap, MessageSquare, RefreshCw, Send, ShieldCheck, UserRound,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/auth/AuthContext";
import { ApiError } from "@/api/kairos-client";
import {
  duringInternshipApi,
  type GriffinEvaluation,
  type Placement,
  type ReportStatus,
  type ReportSubmission,
  type ReportVersion,
  type WorkLog,
  type WorkLogDecision,
} from "@/api/during-internship";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

type WorkspaceRole = "STUDENT" | "FACULTY" | "INDUSTRY_MENTOR";
type WorkLogForm = {
  work_date: string;
  work_summary: string;
  duration_minutes: string;
  tasks_completed: string;
  skills_used: string;
  challenges: string;
  learning_outcomes: string;
  next_steps: string;
};

function localToday(): string {
  const now = new Date();
  return now.getFullYear() + "-" + String(now.getMonth() + 1).padStart(2, "0") + "-" + String(now.getDate()).padStart(2, "0");
}

function emptyWorkLogForm(): WorkLogForm {
  return {
    work_date: localToday(), work_summary: "", duration_minutes: "", tasks_completed: "",
    skills_used: "", challenges: "", learning_outcomes: "", next_steps: "",
  };
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Your session has expired. Sign in again to continue.";
    if (error.status === 403) return "Your account is not authorized for this action.";
    if (error.status === 404) return "This record is no longer available to your account.";
    if (error.status === 409) return error.message;
    if (error.status === 422) return error.message;
    return error.message;
  }
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

function humanize(value: string | null | undefined): string {
  return (value || "Not recorded").replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
}

function dateLabel(value: string | null | undefined): string {
  if (!value) return "Not recorded";
  const parsed = new Date(value + (value.length === 10 ? "T00:00:00" : ""));
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(parsed);
}

function statusVariant(value: string): "default" | "secondary" | "outline" | "destructive" {
  if (["APPROVED", "COMPLETED", "ONGOING"].includes(value)) return "secondary";
  if (["REJECTED", "TERMINATED", "FAILED"].includes(value)) return "destructive";
  if (["SUBMITTED", "UNDER_EVALUATION", "PROCESSING", "QUEUED"].includes(value)) return "default";
  return "outline";
}

function StatusBadge({ value }: { value: string }) {
  return <Badge variant={statusVariant(value)}>{humanize(value)}</Badge>;
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed px-5 py-10 text-center">
      <BriefcaseBusiness className="mb-3 size-8 text-muted-foreground" aria-hidden="true" />
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-1 max-w-lg text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

export default function DuringInternshipPage() {
  const { account } = useAuth();
  const roles = useMemo(() => new Set((account?.roles || []).map((value) => value.toUpperCase())), [account?.roles]);
  const role: WorkspaceRole | null = roles.has("STUDENT") ? "STUDENT"
    : roles.has("FACULTY") ? "FACULTY"
      : ["EMPLOYER", "RECRUITER", "EMPLOYER_ADMIN", "EMPLOYER_MEMBER"].some((item) => roles.has(item)) ? "INDUSTRY_MENTOR" : null;

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [placements, setPlacements] = useState<Placement[]>([]);
  const [workLogs, setWorkLogs] = useState<WorkLog[]>([]);
  const [placementLogs, setPlacementLogs] = useState<WorkLog[]>([]);
  const [reports, setReports] = useState<ReportSubmission[]>([]);
  const [selectedPlacementId, setSelectedPlacementId] = useState("");
  const [editingLog, setEditingLog] = useState<WorkLog | null>(null);
  const [workLogForm, setWorkLogForm] = useState<WorkLogForm>(emptyWorkLogForm);
  const [savingLog, setSavingLog] = useState(false);
  const [reviewingLogId, setReviewingLogId] = useState("");
  const [reviewDecision, setReviewDecision] = useState<WorkLogDecision>("COMMENTED");
  const [reviewFeedback, setReviewFeedback] = useState("");
  const [reviewingReportId, setReviewingReportId] = useState("");
  const [reportFeedback, setReportFeedback] = useState("");
  const [reportTitle, setReportTitle] = useState("");
  const [reportNotes, setReportNotes] = useState("");
  const [reportFile, setReportFile] = useState<File | null>(null);
  const [reportFileInputKey, setReportFileInputKey] = useState(0);
  const [revisionReportId, setRevisionReportId] = useState("");
  const [savingReport, setSavingReport] = useState(false);
  const [versionsByReport, setVersionsByReport] = useState<Record<string, ReportVersion[]>>({});
  const [selectedVersion, setSelectedVersion] = useState<ReportVersion | null>(null);
  const [evaluationByVersion, setEvaluationByVersion] = useState<Record<string, GriffinEvaluation | null>>({});
  const [evaluationProjectId, setEvaluationProjectId] = useState("");
  const [evaluationReportId, setEvaluationReportId] = useState("");
  const [evaluationBusy, setEvaluationBusy] = useState(false);
  const [industryMentorAccountId, setIndustryMentorAccountId] = useState("");
  const [assigningMentor, setAssigningMentor] = useState(false);

  const selectedPlacement = placements.find((item) => item.id === selectedPlacementId) || null;
  const selectedReport = reports.find((item) => item.id === reviewingReportId) || null;
  const displayedLogs = role === "STUDENT" ? workLogs : placementLogs;

  const loadWorkspace = useCallback(async () => {
    if (!role) {
      setLoading(false);
      setLoadError("");
      return;
    }
    setLoading(true);
    setLoadError("");
    try {
      if (role === "STUDENT") {
        const [placementResult, logResult, reportResult] = await Promise.all([
          duringInternshipApi.studentPlacements(),
          duringInternshipApi.workLogsMine(),
          duringInternshipApi.myReports(),
        ]);
        setPlacements(placementResult.items);
        setWorkLogs(logResult.items);
        setReports(reportResult.items);
        setSelectedPlacementId((current) => placementResult.items.some((item) => item.id === current)
          ? current : (placementResult.items.find((item) => item.status === "ONGOING") || placementResult.items[0])?.id || "");
      } else if (role === "FACULTY") {
        const [placementResult, reportResult] = await Promise.all([
          duringInternshipApi.supervisedPlacements(),
          duringInternshipApi.supervisedReports(),
        ]);
        setPlacements(placementResult.items);
        setReports(reportResult.items);
        setWorkLogs([]);
        setSelectedPlacementId((current) => placementResult.items.some((item) => item.id === current)
          ? current : placementResult.items[0]?.id || "");
      } else {
        const placementResult = await duringInternshipApi.mentorPlacements();
        setPlacements(placementResult.items);
        setReports([]);
        setWorkLogs([]);
        setSelectedPlacementId((current) => placementResult.items.some((item) => item.id === current)
          ? current : placementResult.items[0]?.id || "");
      }
    } catch (error) {
      setLoadError(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [role]);

  const loadSelectedLogs = useCallback(async () => {
    if (!role || role === "STUDENT" || !selectedPlacementId) {
      if (role !== "STUDENT") setPlacementLogs([]);
      return;
    }
    try {
      const result = await duringInternshipApi.workLogsForPlacement(selectedPlacementId);
      setPlacementLogs(result.items);
    } catch (error) {
      setLoadError(errorMessage(error));
    }
  }, [role, selectedPlacementId]);

  useEffect(() => { void loadWorkspace(); }, [loadWorkspace]);
  useEffect(() => { void loadSelectedLogs(); }, [loadSelectedLogs]);

  function editWorkLog(item: WorkLog) {
    setSelectedPlacementId(item.placement_id);
    setEditingLog(item);
    setWorkLogForm({
      work_date: item.work_date,
      work_summary: item.work_summary,
      duration_minutes: item.duration_minutes == null ? "" : String(item.duration_minutes),
      tasks_completed: item.tasks_completed || "",
      skills_used: (item.skills_used || []).join(", "),
      challenges: item.challenges || "",
      learning_outcomes: item.learning_outcomes || "",
      next_steps: item.next_steps || "",
    });
  }

  async function saveWorkLog(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPlacementId) {
      toast.error("No internship placement is available for this work log.");
      return;
    }
    const payload = {
      work_date: workLogForm.work_date,
      work_summary: workLogForm.work_summary.trim(),
      duration_minutes: workLogForm.duration_minutes ? Number(workLogForm.duration_minutes) : null,
      tasks_completed: workLogForm.tasks_completed.trim() || null,
      skills_used: workLogForm.skills_used.split(",").map((item) => item.trim()).filter(Boolean),
      challenges: workLogForm.challenges.trim() || null,
      learning_outcomes: workLogForm.learning_outcomes.trim() || null,
      next_steps: workLogForm.next_steps.trim() || null,
    };
    setSavingLog(true);
    try {
      if (editingLog) await duringInternshipApi.updateWorkLog(editingLog.id, payload);
      else await duringInternshipApi.createWorkLog(selectedPlacementId, payload);
      toast.success(editingLog ? "Work log updated." : "Work log saved as a draft.");
      setEditingLog(null);
      setWorkLogForm(emptyWorkLogForm());
      if (role === "STUDENT") await loadWorkspace();
      else await loadSelectedLogs();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSavingLog(false);
    }
  }

  async function submitWorkLog(item: WorkLog) {
    try {
      const updated = await duringInternshipApi.submitWorkLog(item.id);
      toast.success("Work log submitted.");
      if (role === "STUDENT") await loadWorkspace();
      else setPlacementLogs((current) => current.map((log) => log.id === updated.id ? updated : log));
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function saveWorkLogReview(item: WorkLog) {
    if (!reviewFeedback.trim()) {
      toast.error("Add feedback before submitting this review.");
      return;
    }
    try {
      await duringInternshipApi.reviewWorkLog(item.id, reviewDecision, reviewFeedback.trim());
      toast.success("Review saved.");
      setReviewingLogId("");
      setReviewFeedback("");
      await loadSelectedLogs();
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function loadVersions(report: ReportSubmission) {
    try {
      const result = await duringInternshipApi.reportVersions(report.id);
      setVersionsByReport((current) => ({ ...current, [report.id]: result.items }));
      if (result.items.length > 0) await chooseVersion(result.items[0]);
      else setSelectedVersion(null);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function chooseVersion(version: ReportVersion) {
    setSelectedVersion(version);
    try {
      const result = await duringInternshipApi.evaluationForVersion(version.id);
      setEvaluationByVersion((current) => ({ ...current, [version.id]: result.item }));
    } catch (error) {
      // Non-faculty/student report readers may not have evaluation access. Do not invent a status.
      setEvaluationByVersion((current) => ({ ...current, [version.id]: null }));
      if (role === "FACULTY") toast.error(errorMessage(error));
    }
  }

  async function downloadVersion(version: ReportVersion) {
    try {
      const result = await duringInternshipApi.downloadFile(version.file_id);
      const url = URL.createObjectURL(result.blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = result.filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function submitReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reportFile) {
      toast.error("Choose a report file first.");
      return;
    }
    if (!revisionReportId && !selectedPlacementId) {
      toast.error("You need an active placement before submitting a report.");
      return;
    }
    if (!revisionReportId && reportTitle.trim().length < 2) {
      toast.error("Enter a report title with at least 2 characters.");
      return;
    }
    setSavingReport(true);
    try {
      const upload = await duringInternshipApi.uploadFile(reportFile);
      let submissionId = revisionReportId;
      if (revisionReportId) {
        await duringInternshipApi.addReportVersion(revisionReportId, upload.id, reportNotes.trim());
      } else {
        const created = await duringInternshipApi.createReport(selectedPlacementId, reportTitle.trim(), upload.id, reportNotes.trim());
        submissionId = created.id;
      }
      await duringInternshipApi.submitReport(submissionId);
      toast.success("Report submitted to the assigned faculty supervisor.");
      setReportTitle("");
      setReportNotes("");
      setReportFile(null);
      setReportFileInputKey((value) => value + 1);
      setRevisionReportId("");
      await loadWorkspace();
    } catch (error) {
      toast.error("The workflow did not fully complete: " + errorMessage(error) + " Check the report list for any saved draft or version.");
      await loadWorkspace();
    } finally {
      setSavingReport(false);
    }
  }

  async function reviewReport(status: Exclude<ReportStatus, "DRAFT" | "SUBMITTED">) {
    if (!selectedReport) return;
    if (status === "REVISION_REQUIRED" && !reportFeedback.trim()) {
      toast.error("Feedback is required when requesting a revision.");
      return;
    }
    try {
      await duringInternshipApi.reviewReport(selectedReport.id, status, reportFeedback.trim());
      toast.success("Report review saved.");
      setReportFeedback("");
      setReviewingReportId("");
      await loadWorkspace();
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function assignIndustryMentor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPlacementId || !industryMentorAccountId.trim()) return;
    setAssigningMentor(true);
    try {
      await duringInternshipApi.assignIndustryMentor(selectedPlacementId, industryMentorAccountId.trim());
      toast.success("Industry mentor assigned.");
      setIndustryMentorAccountId("");
      await loadWorkspace();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setAssigningMentor(false);
    }
  }

  async function requestEvaluation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedVersion || !evaluationProjectId.trim() || !evaluationReportId.trim()) {
      toast.error("Choose a report version and enter both Griffin identifiers.");
      return;
    }
    setEvaluationBusy(true);
    try {
      const evaluation = await duringInternshipApi.requestEvaluation(
        selectedVersion.id, evaluationProjectId.trim(), evaluationReportId.trim(),
      );
      setEvaluationByVersion((current) => ({ ...current, [selectedVersion.id]: evaluation }));
      toast.success("Evaluation request recorded with status " + humanize(evaluation.current_status) + ".");
      // Re-read server state rather than assuming a job has started.
      const refreshed = await duringInternshipApi.evaluationForVersion(selectedVersion.id);
      setEvaluationByVersion((current) => ({ ...current, [selectedVersion.id]: refreshed.item }));
    } catch (error) {
      toast.error(errorMessage(error));
      if (selectedVersion) {
        try {
          const refreshed = await duringInternshipApi.evaluationForVersion(selectedVersion.id);
          setEvaluationByVersion((current) => ({ ...current, [selectedVersion.id]: refreshed.item }));
        } catch { /* Preserve the last known response and show the dispatch error. */ }
      }
    } finally {
      setEvaluationBusy(false);
    }
  }

  if (!role) {
    return (
      <Alert variant="destructive">
        <AlertCircle />
        <AlertTitle>Internship workspace unavailable</AlertTitle>
        <AlertDescription>This workspace is available to students, assigned faculty supervisors, and authorized employer mentor accounts.</AlertDescription>
      </Alert>
    );
  }

  const isStudent = role === "STUDENT";
  const isFaculty = role === "FACULTY";
  const visibleLogs = role === "STUDENT" ? workLogs : placementLogs;

  return (
    <div className="space-y-6 pb-8">
      <div className="flex flex-col justify-between gap-3 border-b pb-5 sm:flex-row sm:items-end">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
            <BriefcaseBusiness className="size-4" aria-hidden="true" />
            <span>Internship workspace</span>
            <span aria-hidden="true">/</span>
            <span>{isStudent ? "Student" : isFaculty ? "Faculty mentor" : "Industry mentor"}</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">During Internship</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            {isStudent ? "Record your work, submit reports, and follow up on real supervisor feedback."
              : isFaculty ? "Supervise assigned placements, review reports, and inspect the persisted evaluation state."
                : "Review work logs for interns explicitly assigned to you."}
          </p>
        </div>
        <Button variant="outline" onClick={() => void loadWorkspace()} disabled={loading}>
          <RefreshCw className={"mr-2 size-4" + (loading ? " animate-spin" : "")} />
          Refresh
        </Button>
      </div>

      {loadError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertTitle>Could not load all internship data</AlertTitle>
          <AlertDescription>{loadError}</AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="space-y-3" role="status" aria-label="Loading internship workspace">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-56 w-full" />
        </div>
      ) : (
        <Tabs defaultValue="overview" className="space-y-5">
          <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            {isStudent && <TabsTrigger value="work-logs">Work logs</TabsTrigger>}
            {!isStudent && <TabsTrigger value="work-logs">Work log reviews</TabsTrigger>}
            {(isStudent || isFaculty) && <TabsTrigger value="reports">Reports</TabsTrigger>}
            <TabsTrigger value="feedback">Feedback</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-5">
            {placements.length === 0 ? (
              <EmptyState
                title={isStudent ? "No placement recorded yet" : "No assigned placements"}
                description={isStudent
                  ? "Your internship workspace will appear here after an authorized placement is created. Recruitment applications alone are not treated as placements."
                  : "No placements are currently assigned to this account. Ask the institution or employer administrator to verify the placement and mentor assignment."}
              />
            ) : (
              <>
                {isStudent && placements.length > 1 && (
                  <div className="max-w-md space-y-2">
                    <Label htmlFor="student-placement">Internship placement</Label>
                    <NativeSelect id="student-placement" value={selectedPlacementId} onChange={(event) => setSelectedPlacementId(event.target.value)} className="w-full">
                      {placements.map((item) => <option key={item.id} value={item.id}>{item.opportunity.title} · {item.opportunity.company_name || "Employer"}</option>)}
                    </NativeSelect>
                  </div>
                )}
                {selectedPlacement && (
                  <Card>
                    <CardHeader className="gap-3 border-b sm:flex-row sm:items-start sm:justify-between">
                      <div className="space-y-1">
                        <CardDescription>Current placement</CardDescription>
                        <CardTitle className="text-xl">{selectedPlacement.opportunity.title}</CardTitle>
                        <p className="text-sm text-muted-foreground">{selectedPlacement.opportunity.company_name || "Employer not recorded"} · {selectedPlacement.opportunity.location || "Location not recorded"}</p>
                      </div>
                      <StatusBadge value={selectedPlacement.status} />
                    </CardHeader>
                    <CardContent className="grid gap-5 pt-2 sm:grid-cols-2 lg:grid-cols-4">
                      <div className="flex gap-3">
                        <CalendarDays className="mt-0.5 size-4 text-muted-foreground" />
                        <div><p className="text-xs text-muted-foreground">Start date</p><p className="mt-1 font-medium">{dateLabel(selectedPlacement.start_date)}</p></div>
                      </div>
                      <div className="flex gap-3">
                        <CalendarDays className="mt-0.5 size-4 text-muted-foreground" />
                        <div><p className="text-xs text-muted-foreground">End date</p><p className="mt-1 font-medium">{dateLabel(selectedPlacement.end_date)}</p></div>
                      </div>
                      <div className="flex gap-3">
                        <GraduationCap className="mt-0.5 size-4 text-muted-foreground" />
                        <div><p className="text-xs text-muted-foreground">Faculty mentor</p><p className="mt-1 font-medium">{selectedPlacement.faculty_supervisor_name || "Not assigned"}</p></div>
                      </div>
                      <div className="flex gap-3">
                        <UserRound className="mt-0.5 size-4 text-muted-foreground" />
                        <div><p className="text-xs text-muted-foreground">Industry mentor</p><p className="mt-1 font-medium">{selectedPlacement.industry_mentor_name || "Not assigned"}</p></div>
                      </div>
                    </CardContent>
                  </Card>
                )}
                {!isStudent && (
                  <div className="space-y-3">
                    <h2 className="text-base font-semibold">{isFaculty ? "Supervised placements" : "Your assigned interns"}</h2>
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                      {placements.map((item) => (
                        <button key={item.id} type="button" onClick={() => setSelectedPlacementId(item.id)} className={"rounded-lg border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring " + (selectedPlacementId === item.id ? "border-primary bg-primary/5" : "hover:bg-muted/40")}>
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0"><p className="truncate font-medium">{item.student.name}</p><p className="mt-1 truncate text-sm text-muted-foreground">{item.opportunity.title}</p></div>
                            <StatusBadge value={item.status} />
                          </div>
                          <p className="mt-3 text-xs text-muted-foreground">{item.opportunity.company_name || "Employer not recorded"} · {item.student.enrollment_number || "Enrollment not recorded"}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {isFaculty && selectedPlacement && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Industry mentor assignment</CardTitle>
                      <CardDescription>Assign a verified account that is already an active member of the employer organization associated with this placement. The backend validates the relationship.</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <form onSubmit={assignIndustryMentor} className="flex flex-col gap-3 sm:flex-row sm:items-end">
                        <div className="flex-1 space-y-2">
                          <Label htmlFor="mentor-account-id">Mentor account ID</Label>
                          <Input id="mentor-account-id" value={industryMentorAccountId} onChange={(event) => setIndustryMentorAccountId(event.target.value)} placeholder="Account ID provided by your institution" required maxLength={36} />
                        </div>
                        <Button type="submit" disabled={assigningMentor || !industryMentorAccountId.trim()}>
                          <UserRound className="mr-2 size-4" />{assigningMentor ? "Assigning…" : "Assign mentor"}
                        </Button>
                      </form>
                    </CardContent>
                  </Card>
                )}
                <div className="grid gap-4 md:grid-cols-3">
                  <Card size="sm">
                    <CardContent className="flex items-center gap-3 pt-3">
                      <div className="rounded-md bg-muted p-2"><BookOpen className="size-4" /></div>
                      <div><p className="text-xl font-semibold tabular-nums">{isStudent ? workLogs.length : placementLogs.length}</p><p className="text-xs text-muted-foreground">Work logs loaded</p></div>
                    </CardContent>
                  </Card>
                  {(isStudent || isFaculty) && <Card size="sm">
                    <CardContent className="flex items-center gap-3 pt-3">
                      <div className="rounded-md bg-muted p-2"><FileText className="size-4" /></div>
                      <div><p className="text-xl font-semibold tabular-nums">{reports.length}</p><p className="text-xs text-muted-foreground">Report submissions</p></div>
                    </CardContent>
                  </Card>}
                  <Card size="sm">
                    <CardContent className="flex items-center gap-3 pt-3">
                      <div className="rounded-md bg-muted p-2"><MessageSquare className="size-4" /></div>
                      <div><p className="text-xl font-semibold tabular-nums">{(isStudent ? workLogs : placementLogs).reduce((total, item) => total + (item.latest_reviews || []).length, 0)}</p><p className="text-xs text-muted-foreground">Latest work-log reviews</p></div>
                    </CardContent>
                  </Card>
                </div>
                <Alert>
                  <ShieldCheck />
                  <AlertTitle>Progress reflects persisted records</AlertTitle>
                  <AlertDescription>Completion percentages and milestone checkmarks are intentionally omitted because this API does not expose a persisted milestone workflow.</AlertDescription>
                </Alert>
              </>
            )}
          </TabsContent>

          <TabsContent value="work-logs" className="space-y-5">
            {isStudent && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{editingLog ? "Edit work log" : "Record work"}</CardTitle>
                  <CardDescription>Saved logs remain drafts until you submit them. After submission, edits are enabled only if a mentor requests revision.</CardDescription>
                </CardHeader>
                <CardContent>
                  {!selectedPlacement || selectedPlacement.status !== "ONGOING" ? (
                    <Alert><AlertCircle /><AlertTitle>Work logging unavailable</AlertTitle><AlertDescription>A recorded ongoing placement with valid start and end dates is required before a work log can be created.</AlertDescription></Alert>
                  ) : (
                    <form onSubmit={saveWorkLog} className="space-y-4">
                      <div className="grid gap-4 sm:grid-cols-2">
                        <div className="space-y-2"><Label htmlFor="work-date">Work date *</Label><Input id="work-date" type="date" min={selectedPlacement.start_date} max={selectedPlacement.end_date} value={workLogForm.work_date} onChange={(event) => setWorkLogForm((current) => ({ ...current, work_date: event.target.value }))} required /></div>
                        <div className="space-y-2"><Label htmlFor="duration">Duration (minutes, optional)</Label><Input id="duration" type="number" min="1" max="1440" value={workLogForm.duration_minutes} onChange={(event) => setWorkLogForm((current) => ({ ...current, duration_minutes: event.target.value }))} placeholder="e.g. 360" /></div>
                      </div>
                      <div className="space-y-2"><Label htmlFor="work-summary">Work summary *</Label><Textarea id="work-summary" minLength={3} maxLength={10000} value={workLogForm.work_summary} onChange={(event) => setWorkLogForm((current) => ({ ...current, work_summary: event.target.value }))} required placeholder="Summarize the work performed and its outcome." /></div>
                      <div className="space-y-2"><Label htmlFor="tasks-completed">Tasks completed</Label><Textarea id="tasks-completed" value={workLogForm.tasks_completed} onChange={(event) => setWorkLogForm((current) => ({ ...current, tasks_completed: event.target.value }))} placeholder="Key tasks or deliverables" /></div>
                      <div className="space-y-2"><Label htmlFor="skills-used">Skills and technologies</Label><Input id="skills-used" value={workLogForm.skills_used} onChange={(event) => setWorkLogForm((current) => ({ ...current, skills_used: event.target.value }))} placeholder="Python, SQL, testing (comma-separated)" /></div>
                      <div className="grid gap-4 md:grid-cols-3">
                        <div className="space-y-2"><Label htmlFor="challenges">Challenges</Label><Textarea id="challenges" value={workLogForm.challenges} onChange={(event) => setWorkLogForm((current) => ({ ...current, challenges: event.target.value }))} /></div>
                        <div className="space-y-2"><Label htmlFor="learning-outcomes">Learning outcomes</Label><Textarea id="learning-outcomes" value={workLogForm.learning_outcomes} onChange={(event) => setWorkLogForm((current) => ({ ...current, learning_outcomes: event.target.value }))} /></div>
                        <div className="space-y-2"><Label htmlFor="next-steps">Next steps</Label><Textarea id="next-steps" value={workLogForm.next_steps} onChange={(event) => setWorkLogForm((current) => ({ ...current, next_steps: event.target.value }))} /></div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button type="submit" disabled={savingLog || !workLogForm.work_summary.trim()}><Check className="mr-2 size-4" />{savingLog ? "Saving…" : editingLog ? "Save changes" : "Save draft"}</Button>
                        {editingLog && <Button type="button" variant="outline" onClick={() => { setEditingLog(null); setWorkLogForm(emptyWorkLogForm()); }}>Cancel edit</Button>}
                      </div>
                    </form>
                  )}
                </CardContent>
              </Card>
            )}

            {!isStudent && !selectedPlacement && <EmptyState title="Select an assigned placement" description="Choose one of the placements in Overview to inspect its work logs." />}
            {visibleLogs.length === 0 ? (
              <EmptyState title={isStudent ? "No work logs yet" : "No work logs for this placement"} description={isStudent ? "Create a draft above to start documenting your internship activity." : "Submitted work logs will appear here when the student records and submits them."} />
            ) : (
              <div className="space-y-3">
                {visibleLogs.map((item) => {
                  const needsRevision = (item.latest_reviews || []).some((review) => review.decision === "REVISION_REQUIRED");
                  const canEdit = item.status === "DRAFT" || (item.status === "SUBMITTED" && needsRevision);
                  return (
                    <Card key={item.id} size="sm">
                      <CardHeader className="flex-row items-start justify-between gap-4">
                        <div className="min-w-0 space-y-1">
                          <CardDescription>{dateLabel(item.work_date)}{item.duration_minutes ? " · " + item.duration_minutes + " min" : ""}{item.updated_at ? " · Updated " + dateLabel(item.updated_at) : ""}</CardDescription>
                          <CardTitle className="whitespace-normal text-base">{item.work_summary}</CardTitle>
                        </div>
                        <StatusBadge value={item.status} />
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {item.tasks_completed && <p className="whitespace-pre-wrap text-sm"><span className="font-medium">Tasks: </span>{item.tasks_completed}</p>}
                        {!!item.skills_used?.length && <div className="flex flex-wrap gap-1.5">{item.skills_used.map((skill) => <Badge key={skill} variant="outline">{skill}</Badge>)}</div>}
                        <div className="grid gap-3 sm:grid-cols-3">
                          {item.challenges && <div><p className="text-xs font-medium text-muted-foreground">Challenges</p><p className="mt-1 whitespace-pre-wrap text-sm">{item.challenges}</p></div>}
                          {item.learning_outcomes && <div><p className="text-xs font-medium text-muted-foreground">Learning outcomes</p><p className="mt-1 whitespace-pre-wrap text-sm">{item.learning_outcomes}</p></div>}
                          {item.next_steps && <div><p className="text-xs font-medium text-muted-foreground">Next steps</p><p className="mt-1 whitespace-pre-wrap text-sm">{item.next_steps}</p></div>}
                        </div>
                        {!!item.reviews?.length && (
                          <div className="space-y-2 rounded-lg bg-muted/40 p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Review history</p>
                            {item.reviews.map((review) => <div key={review.id} className="border-l-2 pl-3">
                              <div className="flex flex-wrap items-center gap-2 text-xs"><span className="font-medium">{review.reviewer_name || humanize(review.reviewer_role)}</span><StatusBadge value={review.decision} /><span className="text-muted-foreground">{dateLabel(review.created_at)}</span></div>
                              <p className="mt-1 whitespace-pre-wrap text-sm">{review.feedback}</p>
                            </div>)}
                          </div>
                        )}
                        <Separator />
                        <div className="flex flex-wrap gap-2">
                          {isStudent && canEdit && <Button variant="outline" size="sm" onClick={() => editWorkLog(item)}><FileText className="mr-2 size-4" />Edit</Button>}
                          {isStudent && item.status === "DRAFT" && <Button size="sm" onClick={() => void submitWorkLog(item)}><Send className="mr-2 size-4" />Submit for review</Button>}
                          {!isStudent && item.status === "SUBMITTED" && (
                            <Button variant="outline" size="sm" onClick={() => { setReviewingLogId(reviewingLogId === item.id ? "" : item.id); setReviewFeedback(""); }}>
                              <MessageSquare className="mr-2 size-4" />{reviewingLogId === item.id ? "Close review" : "Review work log"}
                            </Button>
                          )}
                        </div>
                        {!isStudent && reviewingLogId === item.id && (
                          <div className="space-y-3 rounded-lg border p-3">
                            <div className="space-y-2"><Label htmlFor={"review-decision-" + item.id}>Review outcome</Label><NativeSelect id={"review-decision-" + item.id} value={reviewDecision} onChange={(event) => setReviewDecision(event.target.value as WorkLogDecision)} className="w-full sm:max-w-xs">
                              <option value="COMMENTED">Feedback only</option><option value="APPROVED">Approve work log</option><option value="REVISION_REQUIRED">Request revision</option>
                            </NativeSelect></div>
                            <div className="space-y-2"><Label htmlFor={"review-feedback-" + item.id}>Feedback *</Label><Textarea id={"review-feedback-" + item.id} value={reviewFeedback} onChange={(event) => setReviewFeedback(event.target.value)} minLength={1} maxLength={5000} required placeholder="Share specific observations and next steps." /></div>
                            <Button onClick={() => void saveWorkLogReview(item)} disabled={!reviewFeedback.trim()}>Submit review</Button>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>

          {(isStudent || isFaculty) && <TabsContent value="reports" className="space-y-5">
            {isStudent && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{revisionReportId ? "Resubmit revised report" : "Submit a report"}</CardTitle>
                  <CardDescription>Files are uploaded to Kairos private storage. A report/version is submitted only after the API confirms the workflow transition.</CardDescription>
                </CardHeader>
                <CardContent>
                  {(!selectedPlacement || selectedPlacement.status !== "ONGOING") && !revisionReportId ? (
                    <Alert><AlertCircle /><AlertTitle>Report submission unavailable</AlertTitle><AlertDescription>Select an ongoing placement first. Recruitment applications do not count as an internship placement.</AlertDescription></Alert>
                  ) : (
                    <form onSubmit={submitReport} className="space-y-4">
                      {revisionReportId ? (
                        <Alert><FileText /><AlertTitle>Revision for report</AlertTitle><AlertDescription>{reports.find((item) => item.id === revisionReportId)?.title || revisionReportId}. The existing report version will be preserved.</AlertDescription></Alert>
                      ) : <div className="space-y-2"><Label htmlFor="report-title">Report title *</Label><Input id="report-title" value={reportTitle} onChange={(event) => setReportTitle(event.target.value)} required minLength={2} maxLength={255} placeholder="Weekly report, midterm report, final report…" /></div>}
                      <div className="space-y-2"><Label htmlFor="report-file">Report file (PDF, image, or text) *</Label><Input id="report-file" type="file" accept=".pdf,.png,.jpg,.jpeg,.txt,application/pdf,image/png,image/jpeg,text/plain" key={reportFileInputKey} onChange={(event) => setReportFile(event.target.files?.[0] || null)} required /></div>
                      <div className="space-y-2"><Label htmlFor="report-notes">Submission notes</Label><Textarea id="report-notes" maxLength={5000} value={reportNotes} onChange={(event) => setReportNotes(event.target.value)} placeholder="Brief context for the reviewer (optional)" /></div>
                      <div className="flex flex-wrap gap-2">
                        <Button type="submit" disabled={savingReport || !reportFile}><Send className="mr-2 size-4" />{savingReport ? "Submitting…" : revisionReportId ? "Upload revision & resubmit" : "Upload & submit report"}</Button>
                        {revisionReportId && <Button type="button" variant="outline" onClick={() => { setRevisionReportId(""); setReportFile(null); setReportFileInputKey((value) => value + 1); }}>Cancel revision</Button>}
                      </div>
                    </form>
                  )}
                </CardContent>
              </Card>
            )}

            {reports.length === 0 ? (
              <EmptyState title={isStudent ? "No report submissions" : "No reports awaiting your supervision"} description={isStudent ? "Create a report submission for an ongoing placement when you are ready." : "Reports are listed here only when their placement is assigned to your faculty supervisor profile."} />
            ) : (
              <div className="space-y-3">
                {reports.map((report) => {
                  const placement = placements.find((item) => item.id === report.placement_id);
                  return <Card key={report.id} size="sm">
                    <CardHeader className="flex-row items-start justify-between gap-4">
                      <div className="min-w-0 space-y-1">
                        <CardTitle className="whitespace-normal text-base">{report.title}</CardTitle>
                        <CardDescription>{placement ? placement.student.name + " · " + placement.opportunity.title : "Placement " + report.placement_id}</CardDescription>
                        <p className="text-xs text-muted-foreground">Updated {dateLabel(report.updated_at)} · Version {report.latest_version_number}</p>
                      </div>
                      <StatusBadge value={report.status} />
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {report.review_feedback && <Alert><MessageSquare /><AlertTitle>Latest review feedback</AlertTitle><AlertDescription className="whitespace-pre-wrap">{report.review_feedback}</AlertDescription></Alert>}
                      <div className="flex flex-wrap gap-2">
                        <Button variant="outline" size="sm" onClick={() => void loadVersions(report)}><FileText className="mr-2 size-4" />Version history</Button>
                        {isStudent && report.status === "DRAFT" && <Button size="sm" onClick={async () => { try { await duringInternshipApi.submitReport(report.id); toast.success("Report submitted."); await loadWorkspace(); } catch (error) { toast.error(errorMessage(error)); } }}><Send className="mr-2 size-4" />Submit draft</Button>}
                        {isStudent && report.status === "REVISION_REQUIRED" && <Button size="sm" onClick={() => { setRevisionReportId(report.id); setReportTitle(report.title); }}><RefreshCw className="mr-2 size-4" />Submit revision</Button>}
                        {isFaculty && ["SUBMITTED", "UNDER_EVALUATION"].includes(report.status) && <Button variant="outline" size="sm" onClick={() => { setReviewingReportId(reviewingReportId === report.id ? "" : report.id); setReportFeedback(""); }}>{reviewingReportId === report.id ? "Close review" : "Review report"}</Button>}
                      </div>
                      {versionsByReport[report.id] && <div className="space-y-2 rounded-lg border p-3">
                        <p className="text-sm font-medium">Stored versions</p>
                        {versionsByReport[report.id].length === 0 ? <p className="text-sm text-muted-foreground">No file versions found.</p> : versionsByReport[report.id].map((version) => (
                          <div key={version.id} className="flex flex-col justify-between gap-2 rounded-md bg-muted/30 p-2 sm:flex-row sm:items-center">
                            <div><p className="text-sm font-medium">Version {version.version_number}</p><p className="text-xs text-muted-foreground">{dateLabel(version.submitted_at)}{version.submission_notes ? " · " + version.submission_notes : ""}</p></div>
                            <div className="flex flex-wrap gap-2">
                              <Button size="sm" variant="outline" onClick={() => void chooseVersion(version)}>Evaluation status</Button>
                              <Button size="sm" variant="outline" onClick={() => void downloadVersion(version)}><ArrowDownToLine className="mr-2 size-4" />Download</Button>
                            </div>
                          </div>
                        ))}
                        {selectedVersion && selectedVersion.submission_id === report.id && isFaculty && (
                          <div className="space-y-3 border-t pt-3">
                            <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-medium">Griffin evaluation</span><StatusBadge value={evaluationByVersion[selectedVersion.id]?.current_status || "NOT_REQUESTED"} /></div>
                            {evaluationByVersion[selectedVersion.id] && <p className="break-all text-xs text-muted-foreground">Job ID: {evaluationByVersion[selectedVersion.id]?.griffin_job_id || "No validated job identifier recorded"}</p>}
                            <form onSubmit={requestEvaluation} className="grid gap-3 md:grid-cols-3">
                              <div className="space-y-2"><Label htmlFor="griffin-project-id">Griffin project ID</Label><Input id="griffin-project-id" value={evaluationProjectId} onChange={(event) => setEvaluationProjectId(event.target.value)} required maxLength={128} /></div>
                              <div className="space-y-2"><Label htmlFor="griffin-report-id">Griffin report ID</Label><Input id="griffin-report-id" value={evaluationReportId} onChange={(event) => setEvaluationReportId(event.target.value)} required maxLength={128} /></div>
                              <div className="flex items-end"><Button type="submit" disabled={evaluationBusy || !["SUBMITTED", "UNDER_EVALUATION"].includes(report.status)}><RefreshCw className={"mr-2 size-4" + (evaluationBusy ? " animate-spin" : "")} />{evaluationBusy ? "Requesting…" : "Request evaluation"}</Button></div>
                            </form>
                            <p className="text-xs text-muted-foreground">Kairos records the evaluation state returned by the backend. Processing is shown only when Griffin returns a validated job ID; failed dispatches remain failures.</p>
                          </div>
                        )}
                      </div>}
                      {isFaculty && reviewingReportId === report.id && (
                        <div className="space-y-3 rounded-lg border p-3">
                          <div className="space-y-2"><Label htmlFor={"report-feedback-" + report.id}>Reviewer feedback</Label><Textarea id={"report-feedback-" + report.id} value={reportFeedback} onChange={(event) => setReportFeedback(event.target.value)} maxLength={5000} placeholder="Required when requesting a revision; otherwise optional." /></div>
                          <div className="flex flex-wrap gap-2">
                            <Button variant="outline" onClick={() => void reviewReport("UNDER_EVALUATION")}>Start evaluation</Button>
                            <Button variant="outline" onClick={() => void reviewReport("REVISION_REQUIRED")}>Request revision</Button>
                            <Button onClick={() => void reviewReport("APPROVED")}>Approve report</Button>
                            <Button variant="destructive" onClick={() => void reviewReport("REJECTED")}>Reject report</Button>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>;
                })}
              </div>
            )}
          </TabsContent>}

          <TabsContent value="feedback" className="space-y-5">
            {isStudent ? (
              <>
                <section className="space-y-3">
                  <div><h2 className="text-base font-semibold">Work-log feedback</h2><p className="text-sm text-muted-foreground">Feedback is shown with its reviewer role and recorded decision.</p></div>
                  {workLogs.flatMap((log) => (log.reviews || []).map((review) => ({ log, review }))).length === 0 ? (
                    <EmptyState title="No work-log feedback yet" description="Mentor comments will appear here after they review a submitted work log." />
                  ) : workLogs.flatMap((log) => (log.reviews || []).map((review) => ({ log, review }))).map(({ log, review }) => (
                    <Card key={review.id} size="sm"><CardContent className="space-y-2 pt-3">
                      <div className="flex flex-wrap items-center gap-2"><span className="font-medium">{review.reviewer_name || humanize(review.reviewer_role)}</span><Badge variant="outline">{humanize(review.reviewer_role)}</Badge><StatusBadge value={review.decision} /><span className="text-xs text-muted-foreground">{dateLabel(review.created_at)}</span></div>
                      <p className="text-xs text-muted-foreground">Work log · {dateLabel(log.work_date)} · {log.work_summary}</p>
                      <p className="whitespace-pre-wrap text-sm">{review.feedback}</p>
                    </CardContent></Card>
                  ))}
                </section>
                <Separator />
                <section className="space-y-3">
                  <div><h2 className="text-base font-semibold">Report feedback</h2><p className="text-sm text-muted-foreground">Report feedback is kept distinct from work-log comments and official evaluation outcomes.</p></div>
                  {reports.filter((item) => item.review_feedback).length === 0 ? <EmptyState title="No report feedback recorded" description="Any persisted report-review feedback will appear here." /> : reports.filter((item) => item.review_feedback).map((item) => (
                    <Card key={item.id} size="sm"><CardContent className="space-y-2 pt-3">
                      <div className="flex flex-wrap items-center gap-2"><span className="font-medium">{item.title}</span><StatusBadge value={item.status} /><span className="text-xs text-muted-foreground">{dateLabel(item.reviewed_at)}</span></div>
                      <p className="whitespace-pre-wrap text-sm">{item.review_feedback}</p>
                    </CardContent></Card>
                  ))}
                </section>
              </>
            ) : (
              <EmptyState
                title={isFaculty ? "Supervision feedback history" : "Industry review history"}
                description="Feedback is preserved on each work-log and report record. Open the Work log reviews or Reports tab to inspect its associated review history. This role does not receive an invented aggregate grade or score."
              />
            )}
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
