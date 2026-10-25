import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Activity, AlertCircle, ArrowDownToLine, CheckCircle2, ClipboardCheck, FileText, RefreshCw, Send, ShieldCheck, Upload, XCircle } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiRequest, ApiError, downloadApiFile } from "@/api/kairos-client";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type Placement = {
  id: string;
  status: string;
  start_date: string;
  end_date: string;
  internship_title: string;
  organization_name: string;
  faculty_supervisor_id?: number | null;
};

type Report = {
  id: string;
  placement_id: string;
  title: string;
  latest_version_number: number;
  status: string;
  review_feedback?: string | null;
  created_at?: string;
  updated_at?: string;
};

type ReportVersion = {
  id: string;
  submission_id: string;
  version_number: number;
  file_id: string;
  presentation_file_id?: string | null;
  submission_notes?: string | null;
  submitted_at?: string;
};

type UploadResult = { id: string; original_name: string; file_size_bytes: number; mime_type: string; created_at?: string };
type AcademicResult = {
  id: string;
  report_submission_id: string;
  report_version_id: string;
  title?: string | null;
  semester: number;
  academic_year_id?: string | null;
  revision_number: number;
  component_breakdown: { components?: Record<string, number | null>; weights?: Record<string, number>; policy_version?: number; outcome?: string };
  total_score: number;
  grade: string;
  status: string;
  finalized_at?: string | null;
  published_at?: string | null;
};
type Stage = { key: string; label: string; status: string; detail: string };
type ProgressPayload = { submission_id: string; version_number: number; stages: Stage[] };
type Assignment = { id: string; packet_code: string; report_version_id: string; status: string; assigned_at: string; submitted_at?: string | null; total_score?: number | null };
type SupervisedStudent = { student_profile_id: number; full_name: string; enrollment_number: string; current_semester: number; programme_id?: string | null };
type RubricCriterion = { key: string; label: string; description: string; max_score: number; require_comment?: boolean };
type Score = { score: number; comment?: string | null };
type Packet = {
  id: string;
  packet_code: string;
  status: string;
  version_number: number;
  assigned_at: string;
  rubric: RubricCriterion[];
  scores: Record<string, Score>;
  evaluator_comments?: string | null;
  report_download_url: string;
  presentation_download_url?: string | null;
  curriculum_mapping?: Array<{ outcome_code: string; title: string; expected_competency: string; status: string; evidence_reference?: string | null }>;
  blinding_notice: string;
};
type ScoreDraft = { score: string; comment: string };

const dateLabel = (value?: string | null) => {
  if (!value) return "Not recorded";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not recorded" : date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
};
const dateTimeLabel = (value?: string | null) => {
  if (!value) return "Not recorded";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not recorded" : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
};
const prettyStatus = (value?: string | null) => (value || "UNKNOWN").toLowerCase().replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
const badgeVariant = (status: string): "default" | "secondary" | "outline" | "destructive" => {
  if (["APPROVED", "PUBLISHED", "COMPLETE", "SUBMITTED", "COMPLETED"].includes(status)) return "default";
  if (["FAILED", "REJECTED", "NOT_EVIDENCED", "BLOCKED"].includes(status)) return "destructive";
  if (["PROCESSING", "UNDER_EVALUATION", "FINALIZED", "DRAFT"].includes(status)) return "secondary";
  return "outline";
};
const readableError = (error: unknown) => {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Your session has expired. Sign in again to continue.";
    if (error.status === 403) return "Your account is not authorized for this action.";
    if (error.status === 404) return "The record was not found or is not available to your account.";
    if (error.status === 409) return error.message;
    if (error.status === 413) return "The file is larger than Kairos's 10 MiB upload limit.";
    return error.message;
  }
  return error instanceof Error ? error.message : "Kairos could not be reached. Check your connection and retry.";
};

function PageHeading({ faculty }: { faculty: boolean }) {
  return (
    <div className="mb-6 flex flex-col justify-between gap-4 border-b border-border/80 pb-6 md:flex-row md:items-end">
      <div>
        <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-teal-700">
          <ClipboardCheck className="size-4" /> Internship assessment
        </p>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{faculty ? "Blind assessment workspace" : "Final internship submission"}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          {faculty
            ? "Review the assigned work against the approved rubric. Identity and unreleased assessment data stay out of the blind packet."
            : "Submit your final report and presentation, follow each assessment stage, and view academic outcomes once they are officially published."}
        </p>
      </div>
      <div className="flex items-center gap-2 rounded-full border border-border px-3 py-2 text-xs text-muted-foreground">
        <ShieldCheck className="size-4 text-teal-700" /> Role-restricted academic records
      </div>
    </div>
  );
}

function StateAlert({ title, message, retry }: { title: string; message: string; retry?: () => void }) {
  return (
    <Alert variant="destructive">
      <AlertCircle className="size-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span>{message}</span>
          {retry && <Button variant="outline" size="sm" onClick={retry}><RefreshCw className="mr-2 size-3.5" />Retry</Button>}
        </div>
      </AlertDescription>
    </Alert>
  );
}

function StageTimeline({ stages }: { stages: Stage[] }) {
  return (
    <div className="space-y-3">
      {stages.map((stage, index) => {
        const complete = ["COMPLETE", "PUBLISHED", "COMPLETED", "APPROVED"].includes(stage.status);
        const failed = ["FAILED", "BLOCKED", "REJECTED"].includes(stage.status);
        const Icon = complete ? CheckCircle2 : failed ? XCircle : Activity;
        return (
          <div className="flex gap-3" key={stage.key}>
            <div className="flex flex-col items-center">
              <span className={`flex size-8 shrink-0 items-center justify-center rounded-full border ${complete ? "border-teal-700/30 bg-teal-700/10 text-teal-800" : failed ? "border-destructive/30 bg-destructive/5 text-destructive" : "border-border bg-muted/50 text-muted-foreground"}`}>
                <Icon className="size-4" />
              </span>
              {index < stages.length - 1 && <span className="my-1 min-h-4 w-px flex-1 bg-border" />}
            </div>
            <div className="min-w-0 flex-1 pb-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">{stage.label}</p>
                <Badge variant={badgeVariant(stage.status)}>{prettyStatus(stage.status)}</Badge>
              </div>
              <p className="mt-1 text-sm leading-5 text-muted-foreground">{stage.detail}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function AssessmentWorkspacePage() {
  const { account } = useAuth();
  const roles = useMemo(() => (account?.roles ?? []).map((role) => role.toUpperCase()), [account?.roles]);
  const studentMode = roles.includes("STUDENT");
  const facultyMode = !studentMode && roles.includes("FACULTY");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [notice, setNotice] = useState("");
  const [placements, setPlacements] = useState<Placement[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [results, setResults] = useState<AcademicResult[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [supervisedStudents, setSupervisedStudents] = useState<SupervisedStudent[]>([]);
  const [selectedSupervisedStudentId, setSelectedSupervisedStudentId] = useState("");
  const [supervisedResults, setSupervisedResults] = useState<AcademicResult[]>([]);
  const [supervisedResultLoading, setSupervisedResultLoading] = useState(false);
  const [supervisedResultError, setSupervisedResultError] = useState("");
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [versions, setVersions] = useState<ReportVersion[]>([]);
  const [progress, setProgress] = useState<ProgressPayload | null>(null);
  const [mappingMessage, setMappingMessage] = useState("");
  const [detailLoading, setDetailLoading] = useState(false);
  const [placementId, setPlacementId] = useState("");
  const [reportTitle, setReportTitle] = useState("");
  const [submissionNotes, setSubmissionNotes] = useState("");
  const [reportFile, setReportFile] = useState<File | null>(null);
  const [presentationFile, setPresentationFile] = useState<File | null>(null);
  const [packet, setPacket] = useState<Packet | null>(null);
  const [scoreDraft, setScoreDraft] = useState<Record<string, ScoreDraft>>({});
  const [evaluatorComments, setEvaluatorComments] = useState("");
  const [packetLoading, setPacketLoading] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    setActionError("");
    try {
      if (studentMode) {
        const placementResult = await apiRequest<{ items: Placement[] }>("/modules/internships/placements/me");
        setPlacements(placementResult.items ?? []);
        const reportResult = await apiRequest<{ items: Report[] }>("/reports/me");
        setReports(reportResult.items ?? []);
        const resultData = await apiRequest<{ items: AcademicResult[] }>("/internship-assessments/results/me");
        setResults(resultData.items ?? []);
      } else if (facultyMode) {
        const [result, studentData] = await Promise.all([
          apiRequest<{ items: Assignment[] }>("/internship-assessments/assignments/me"),
          apiRequest<{ items: SupervisedStudent[] }>("/internship-assessments/supervised-students"),
        ]);
        setAssignments(result.items ?? []);
        setSupervisedStudents(studentData.items ?? []);
      } else {
        setLoadError("This workspace is available to student and faculty accounts. Your account has no supported assessment role.");
      }
    } catch (error) {
      setLoadError(readableError(error));
    } finally {
      setLoading(false);
    }
  }, [facultyMode, studentMode]);

  useEffect(() => { void reload(); }, [reload]);

  const openReport = async (report: Report) => {
    setSelectedReport(report);
    setVersions([]);
    setProgress(null);
    setMappingMessage("");
    setDetailLoading(true);
    setActionError("");
    try {
      const [versionData, progressData, mappingData] = await Promise.all([
        apiRequest<{ items: ReportVersion[] }>(`/reports/${encodeURIComponent(report.id)}/versions`),
        apiRequest<ProgressPayload>(`/internship-assessments/submissions/${encodeURIComponent(report.id)}/progress`),
        apiRequest<{ catalogue_available: boolean; message?: string | null }>(`/internship-assessments/submissions/${encodeURIComponent(report.id)}/mappings`),
      ]);
      setVersions(versionData.items ?? []);
      setProgress(progressData);
      setMappingMessage(mappingData.message || (mappingData.catalogue_available ? "Curriculum outcome catalogue is available." : ""));
    } catch (error) {
      setActionError(readableError(error));
    } finally {
      setDetailLoading(false);
    }
  };

  const loadSupervisedResults = async () => {
    if (!selectedSupervisedStudentId) {
      setSupervisedResultError("Select one of your supervised students first.");
      return;
    }
    setSupervisedResultLoading(true);
    setSupervisedResultError("");
    try {
      const data = await apiRequest<{ items: AcademicResult[] }>(
        `/internship-assessments/results/students/${encodeURIComponent(selectedSupervisedStudentId)}`
      );
      setSupervisedResults(data.items ?? []);
    } catch (error) {
      setSupervisedResultError(readableError(error));
      setSupervisedResults([]);
    } finally {
      setSupervisedResultLoading(false);
    }
  };

  const uploadFile = async (file: File): Promise<UploadResult> => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest<UploadResult>("/storage/upload", { method: "POST", body: formData });
  };

  const submitFinalPackage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setActionError("");
    setNotice("");
    const selectedPlacement = placements.find((item) => item.id === placementId);
    if (!selectedPlacement || selectedPlacement.status !== "ONGOING") {
      setActionError("Choose an eligible, ongoing internship placement.");
      return;
    }
    if (!reportTitle.trim() || !reportFile || !presentationFile) {
      setActionError("Enter a title and attach both the report PDF and the PowerPoint presentation.");
      return;
    }
    if (!reportFile.name.toLowerCase().endsWith(".pdf") || reportFile.type !== "application/pdf") {
      setActionError("The report must be a PDF file.");
      return;
    }
    if (!presentationFile.name.toLowerCase().endsWith(".pptx") || presentationFile.type !== "application/vnd.openxmlformats-officedocument.presentationml.presentation") {
      setActionError("The presentation must be a PowerPoint PPTX file.");
      return;
    }
    if (reportFile.size > 10 * 1024 * 1024 || presentationFile.size > 10 * 1024 * 1024) {
      setActionError("Each file must be 10 MiB or smaller.");
      return;
    }
    setBusy(true);
    try {
      const reportUpload = await uploadFile(reportFile);
      const presentationUpload = await uploadFile(presentationFile);
      const report = await apiRequest<Report>("/reports", {
        method: "POST",
        body: JSON.stringify({
          placement_id: placementId,
          title: reportTitle.trim(),
          file_id: reportUpload.id,
          presentation_file_id: presentationUpload.id,
          submission_notes: submissionNotes.trim() || null,
        }),
      });
      await apiRequest(`/reports/${encodeURIComponent(report.id)}/submit`, { method: "POST" });
      setNotice("Your report and presentation were submitted. Kairos will show the next assessment stage when its real status is recorded.");
      setReportTitle("");
      setSubmissionNotes("");
      setReportFile(null);
      setPresentationFile(null);
      setSelectedReport(null);
      await reload();
    } catch (error) {
      // A failed submit may have left a valid draft; reload so it stays visible and recoverable.
      await reload();
      setActionError(readableError(error));
    } finally {
      setBusy(false);
    }
  };

  const openPacket = async (assignment: Assignment) => {
    setPacketLoading(true);
    setActionError("");
    try {
      const data = await apiRequest<Packet>(`/internship-assessments/assignments/${encodeURIComponent(assignment.id)}`);
      setPacket(data);
      setEvaluatorComments(data.evaluator_comments ?? "");
      const initial: Record<string, ScoreDraft> = {};
      for (const criterion of data.rubric) {
        const previous = data.scores?.[criterion.key];
        initial[criterion.key] = { score: previous?.score === undefined ? "" : String(previous.score), comment: previous?.comment ?? "" };
      }
      setScoreDraft(initial);
    } catch (error) {
      setActionError(readableError(error));
    } finally {
      setPacketLoading(false);
    }
  };

  const saveScorePacket = async (submit: boolean) => {
    if (!packet) return;
    setActionError("");
    setNotice("");
    const scores: Record<string, { score: number; comment: string | null }> = {};
    for (const criterion of packet.rubric) {
      const current = scoreDraft[criterion.key];
      if (!current?.score.trim()) {
        if (submit) {
          setActionError(`Enter a score for “${criterion.label}” before submitting.`);
          return;
        }
        continue;
      }
      const score = Number(current.score);
      if (!Number.isFinite(score) || score < 0 || score > criterion.max_score) {
        setActionError(`“${criterion.label}” must be between 0 and ${criterion.max_score}.`);
        return;
      }
      if (submit && criterion.require_comment && !current.comment.trim()) {
        setActionError(`Add a comment for “${criterion.label}” before submitting.`);
        return;
      }
      scores[criterion.key] = { score, comment: current.comment.trim() || null };
    }
    setBusy(true);
    try {
      const path = submit
        ? `/internship-assessments/assignments/${encodeURIComponent(packet.id)}/submit`
        : `/internship-assessments/assignments/${encodeURIComponent(packet.id)}/scores`;
      await apiRequest(path, {
        method: submit ? "POST" : "PUT",
        body: JSON.stringify({ scores, evaluator_comments: evaluatorComments.trim() || null }),
      });
      setNotice(submit ? "Your independent assessment has been submitted and locked." : "Draft assessment saved.");
      if (submit) {
        setPacket(null);
        await reload();
      } else {
        await openPacket({ id: packet.id, packet_code: packet.packet_code, report_version_id: "", status: packet.status, assigned_at: packet.assigned_at });
      }
    } catch (error) {
      setActionError(readableError(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto w-full max-w-7xl pb-8">
      <PageHeading faculty={facultyMode} />
      {loadError && <div className="mb-5"><StateAlert title="Assessment data could not be loaded" message={loadError} retry={() => void reload()} /></div>}
      {actionError && <div className="mb-5"><StateAlert title="Action needs attention" message={actionError} /></div>}
      {notice && <Alert className="mb-5 border-teal-700/25 bg-teal-700/5 text-foreground"><CheckCircle2 className="size-4 text-teal-700" /><AlertTitle>Update</AlertTitle><AlertDescription>{notice}</AlertDescription></Alert>}

      {studentMode && (
        <div className="space-y-6">
          <Card className="rounded-xl border-border/80 shadow-none">
            <CardHeader>
              <CardTitle className="text-base">Final submission package</CardTitle>
              <CardDescription>Attach both files to the same immutable report version. Review the filenames before submitting.</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? <div className="space-y-3"><Skeleton className="h-9 w-full" /><Skeleton className="h-9 w-2/3" /><Skeleton className="h-20 w-full" /></div> : (
                <form onSubmit={submitFinalPackage} className="space-y-5">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="assessment-placement">Internship placement</Label>
                      <Select value={placementId} onValueChange={(value) => setPlacementId(value ?? "")}>
                        <SelectTrigger id="assessment-placement" className="w-full"><SelectValue placeholder="Select an ongoing placement" /></SelectTrigger>
                        <SelectContent>
                          {placements.filter((item) => item.status === "ONGOING").map((item) => (
                            <SelectItem key={item.id} value={item.id}>{item.internship_title} · {item.organization_name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {placements.filter((item) => item.status === "ONGOING").length === 0 && <p className="text-xs text-muted-foreground">No ongoing placement was returned for your account.</p>}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="assessment-title">Report title</Label>
                      <Input id="assessment-title" value={reportTitle} onChange={(event) => setReportTitle(event.target.value)} placeholder="Final internship report title" minLength={2} maxLength={255} required />
                    </div>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="report-pdf">Final report (PDF)</Label>
                      <Input id="report-pdf" type="file" accept=".pdf,application/pdf" onChange={(event) => setReportFile(event.target.files?.[0] ?? null)} required />
                      <p className="text-xs text-muted-foreground">PDF only · maximum 10 MiB</p>
                      {reportFile && <p className="break-all text-sm font-medium">{reportFile.name} <span className="font-normal text-muted-foreground">({(reportFile.size / 1024 / 1024).toFixed(2)} MiB)</span></p>}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="presentation-pptx">Presentation (PowerPoint PPTX)</Label>
                      <Input id="presentation-pptx" type="file" accept=".pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation" onChange={(event) => setPresentationFile(event.target.files?.[0] ?? null)} required />
                      <p className="text-xs text-muted-foreground">PPTX only · maximum 10 MiB</p>
                      {presentationFile && <p className="break-all text-sm font-medium">{presentationFile.name} <span className="font-normal text-muted-foreground">({(presentationFile.size / 1024 / 1024).toFixed(2)} MiB)</span></p>}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="submission-notes">Submission notes (optional)</Label>
                    <Textarea id="submission-notes" value={submissionNotes} onChange={(event) => setSubmissionNotes(event.target.value)} placeholder="Add context for the reviewer, version notes, or a brief summary." maxLength={5000} />
                  </div>
                  <div className="flex flex-col justify-between gap-3 rounded-lg border border-border bg-muted/20 p-4 sm:flex-row sm:items-center">
                    <div className="flex items-start gap-3"><Upload className="mt-0.5 size-4 text-muted-foreground" /><div><p className="text-sm font-medium">Ready to submit?</p><p className="mt-1 text-xs leading-5 text-muted-foreground">Kairos records a new version; it does not overwrite material that has already been assessed.</p></div></div>
                    <Button type="submit" disabled={busy || loading || !placements.some((item) => item.id === placementId && item.status === "ONGOING")}><Send className="mr-2 size-4" />{busy ? "Submitting…" : "Submit report & presentation"}</Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>

          <section className="space-y-3">
            <div><h2 className="text-lg font-semibold tracking-tight">My submissions</h2><p className="mt-1 text-sm text-muted-foreground">Submission history and the latest recorded assessment stage.</p></div>
            {loading && reports.length === 0 ? <div className="grid gap-3 md:grid-cols-2">{[1, 2].map((value) => <Card key={value} className="shadow-none"><CardContent className="space-y-3 p-5"><Skeleton className="h-5 w-2/3" /><Skeleton className="h-4 w-1/2" /><Skeleton className="h-9 w-full" /></CardContent></Card>)}</div> :
              reports.length === 0 ? <Card className="border-dashed shadow-none"><CardContent className="py-10 text-center"><FileText className="mx-auto size-8 text-muted-foreground" /><p className="mt-3 font-medium">No report submissions yet</p><p className="mt-1 text-sm text-muted-foreground">Your submitted internship packages will appear here.</p></CardContent></Card> :
                <div className="grid gap-3 lg:grid-cols-2">{reports.map((report) => (
                  <Card key={report.id} className="rounded-xl border-border/80 shadow-none">
                    <CardContent className="p-5">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0"><p className="font-semibold">{report.title}</p><p className="mt-1 text-xs text-muted-foreground">Updated {dateTimeLabel(report.updated_at)} · version {report.latest_version_number}</p></div>
                        <Badge variant={badgeVariant(report.status)}>{prettyStatus(report.status)}</Badge>
                      </div>
                      {report.review_feedback && <p className="mt-3 rounded-lg border border-border bg-muted/30 p-3 text-sm"><span className="font-medium">Reviewer feedback: </span>{report.review_feedback}</p>}
                      <div className="mt-4 flex flex-wrap gap-2">
                        <Button variant="outline" size="sm" onClick={() => void openReport(report)}><Activity className="mr-2 size-4" />Assessment progress</Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}</div>}
          </section>

          {selectedReport && (
            <Card className="rounded-xl border-border/80 shadow-none">
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-3"><div><CardTitle className="text-base">{selectedReport.title}</CardTitle><CardDescription className="mt-1">Version history and persisted workflow status</CardDescription></div><Button variant="ghost" size="sm" onClick={() => setSelectedReport(null)}>Close</Button></div>
              </CardHeader>
              <CardContent>
                {detailLoading ? <div className="space-y-3"><Skeleton className="h-5 w-1/3" /><Skeleton className="h-20 w-full" /></div> : (
                  <div className="grid gap-7 lg:grid-cols-[1fr_1fr]">
                    <div>
                      <h3 className="mb-4 font-medium">Assessment timeline</h3>
                      {progress ? <StageTimeline stages={progress.stages} /> : <p className="text-sm text-muted-foreground">No persisted stage data was returned.</p>}
                      {mappingMessage && <p className="mt-3 rounded-lg border border-border bg-muted/20 p-3 text-sm text-muted-foreground">{mappingMessage}</p>}
                    </div>
                    <div>
                      <h3 className="mb-4 font-medium">Submission versions</h3>
                      {versions.length === 0 ? <p className="text-sm text-muted-foreground">No version records were returned.</p> : <div className="space-y-3">{versions.map((version) => (
                        <div key={version.id} className="rounded-lg border border-border p-3">
                          <div className="flex flex-wrap items-center justify-between gap-2"><p className="font-medium">Version {version.version_number}</p><span className="text-xs text-muted-foreground">{dateTimeLabel(version.submitted_at)}</span></div>
                          {version.submission_notes && <p className="mt-1 text-sm text-muted-foreground">{version.submission_notes}</p>}
                          <div className="mt-3 flex flex-wrap gap-2">
                            <Button variant="outline" size="sm" onClick={() => void downloadApiFile(`/storage/${encodeURIComponent(version.file_id)}`, `internship-report-v${version.version_number}.pdf`)}><ArrowDownToLine className="mr-2 size-3.5" />Report PDF</Button>
                            {version.presentation_file_id && <Button variant="outline" size="sm" onClick={() => void downloadApiFile(`/storage/${encodeURIComponent(version.presentation_file_id!)}`, `internship-presentation-v${version.version_number}.pptx`)}><ArrowDownToLine className="mr-2 size-3.5" />Presentation</Button>}
                          </div>
                        </div>
                      ))}</div>}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <section className="space-y-3">
            <div><h2 className="text-lg font-semibold tracking-tight">Internship & academic performance</h2><p className="mt-1 text-sm text-muted-foreground">Only published outcomes from Kairos academic records appear in this section.</p></div>
            {results.length >= 2 && (
              <Card className="rounded-xl border-border/80 shadow-none">
                <CardHeader><CardTitle className="text-base">Published internship results over time</CardTitle><CardDescription>Scores are shown on a 0–100 scale; superseded or unpublished results are not included.</CardDescription></CardHeader>
                <CardContent>
                  <div className="h-64 w-full" role="img" aria-label="Line chart showing published internship assessment scores by semester">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={results.map((item, index) => ({ period: `Sem ${item.semester} · ${index + 1}`, score: item.total_score }))} margin={{ top: 8, right: 12, left: -16, bottom: 6 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="period" tickLine={false} axisLine={false} />
                        <YAxis domain={[0, 100]} tickLine={false} axisLine={false} width={38} />
                        <Tooltip formatter={(value) => [`${value} / 100`, "Score"]} />
                        <Line type="monotone" dataKey="score" stroke="var(--color-primary)" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 5 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            )}
            {results.length === 0 ? <Card className="border-dashed shadow-none"><CardContent className="py-8 text-center"><GraduationCapIcon /><p className="mt-3 font-medium">No published internship result yet</p><p className="mt-1 text-sm text-muted-foreground">Results appear after the approved assessment policy is applied and an authorized academic approver publishes the outcome.</p></CardContent></Card> :
              <>
                {results.length < 2 && <p className="rounded-lg border border-border bg-muted/20 p-3 text-sm text-muted-foreground">One published result is available. A trend chart will appear when at least two results exist.</p>}
                <div className="overflow-hidden rounded-xl border border-border">
                  <div className="overflow-x-auto"><table className="w-full min-w-[540px] text-left text-sm"><thead className="bg-muted/50 text-xs text-muted-foreground"><tr><th className="px-4 py-3 font-medium">Assessment</th><th className="px-4 py-3 font-medium">Semester</th><th className="px-4 py-3 font-medium">Score</th><th className="px-4 py-3 font-medium">Grade</th><th className="px-4 py-3 font-medium">Published</th></tr></thead><tbody>{results.map((result) => <tr className="border-t border-border" key={result.id}><td className="px-4 py-3 font-medium">{result.title || "Internship assessment"}</td><td className="px-4 py-3">Semester {result.semester}</td><td className="px-4 py-3 tabular-nums">{result.total_score.toFixed(2)} / 100</td><td className="px-4 py-3"><Badge variant="outline">{result.grade}</Badge></td><td className="px-4 py-3 text-muted-foreground">{dateLabel(result.published_at)}</td></tr>)}</tbody></table></div>
                </div>
              </>}
          </section>
        </div>
      )}

      {facultyMode && (
        <div className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-[minmax(300px,0.85fr)_minmax(0,1.4fr)]">
          <section className="space-y-3">
            <div><h2 className="text-lg font-semibold tracking-tight">My assigned assessments</h2><p className="mt-1 text-sm text-muted-foreground">Only assignments belonging to your authenticated faculty profile are returned.</p></div>
            {loading ? <Card className="shadow-none"><CardContent className="space-y-3 p-5"><Skeleton className="h-5 w-2/3" /><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></CardContent></Card> :
              assignments.length === 0 ? <Card className="border-dashed shadow-none"><CardContent className="py-10 text-center"><ClipboardCheck className="mx-auto size-8 text-muted-foreground" /><p className="mt-3 font-medium">No assigned assessments</p><p className="mt-1 text-sm text-muted-foreground">An authorized supervisor or institution administrator must assign an assessment.</p></CardContent></Card> :
                <div className="space-y-3">{assignments.map((assignment) => (
                  <Card key={assignment.id} className="rounded-xl border-border/80 shadow-none">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-3"><div><p className="font-semibold">Packet {assignment.packet_code}</p><p className="mt-1 text-xs text-muted-foreground">Assigned {dateTimeLabel(assignment.assigned_at)}</p></div><Badge variant={badgeVariant(assignment.status)}>{prettyStatus(assignment.status)}</Badge></div>
                      <div className="mt-4 flex items-center justify-between gap-3"><p className="text-xs text-muted-foreground">{assignment.total_score == null ? "No submitted score" : `Submitted score: ${assignment.total_score}`}</p><Button size="sm" variant="outline" disabled={packetLoading} onClick={() => void openPacket(assignment)}>{assignment.status === "SUBMITTED" ? "View submission" : "Open packet"}</Button></div>
                    </CardContent>
                  </Card>
                ))}</div>}
          </section>

          <section>
            {!packet ? <Card className="h-full min-h-64 border-dashed shadow-none"><CardContent className="flex h-full min-h-64 flex-col items-center justify-center p-8 text-center"><ShieldCheck className="size-9 text-muted-foreground" /><h2 className="mt-3 font-semibold">Blind assessment packet</h2><p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">Select an assigned packet to review the report, presentation, approved rubric, and only the evidence permitted by that assessment policy.</p></CardContent></Card> :
              <Card className="rounded-xl border-border/80 shadow-none">
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3"><div><CardTitle className="text-base">Packet {packet.packet_code}</CardTitle><CardDescription className="mt-1">Report version {packet.version_number} · assigned {dateTimeLabel(packet.assigned_at)}</CardDescription></div><Button variant="ghost" size="sm" onClick={() => setPacket(null)}>Close</Button></div>
                </CardHeader>
                <CardContent className="space-y-5">
                  <Alert><ShieldCheck className="size-4" /><AlertTitle>Blind review</AlertTitle><AlertDescription>{packet.blinding_notice} Do not attempt to identify the student or use information outside the permitted packet.</AlertDescription></Alert>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" onClick={() => void downloadApiFile(packet.report_download_url, "assessment-report.pdf")}><ArrowDownToLine className="mr-2 size-4" />Report PDF</Button>
                    {packet.presentation_download_url && <Button variant="outline" onClick={() => void downloadApiFile(packet.presentation_download_url!, "assessment-presentation.pptx")}><ArrowDownToLine className="mr-2 size-4" />Presentation PPTX</Button>}
                  </div>
                  {packet.curriculum_mapping && packet.curriculum_mapping.length > 0 && <div className="space-y-2"><h3 className="font-medium">Permitted curriculum evidence</h3>{packet.curriculum_mapping.map((item) => <div key={item.outcome_code} className="rounded-lg border border-border p-3"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-medium">{item.outcome_code} · {item.title}</p><Badge variant={badgeVariant(item.status)}>{prettyStatus(item.status)}</Badge></div><p className="mt-1 text-sm text-muted-foreground">{item.expected_competency}</p>{item.evidence_reference && <p className="mt-2 text-sm">Evidence: {item.evidence_reference}</p>}</div>)}</div>}
                  <Separator />
                  <div><h3 className="font-semibold">Scoring rubric</h3><p className="mt-1 text-sm text-muted-foreground">Score each criterion within the range shown. Submitted scores are immutable.</p></div>
                  {packet.rubric.map((criterion) => (
                    <div key={criterion.key} className="space-y-3 rounded-lg border border-border p-4">
                      <div className="flex flex-wrap items-start justify-between gap-2"><div><p className="font-medium">{criterion.label}</p><p className="mt-1 text-sm leading-5 text-muted-foreground">{criterion.description}</p></div><Badge variant="outline">Max {criterion.max_score}</Badge></div>
                      <div className="grid gap-3 md:grid-cols-[150px_1fr]">
                        <div className="space-y-2"><Label htmlFor={`score-${criterion.key}`}>Score</Label><Input id={`score-${criterion.key}`} type="number" min={0} max={criterion.max_score} step="0.5" value={scoreDraft[criterion.key]?.score ?? ""} onChange={(event) => setScoreDraft((current) => ({ ...current, [criterion.key]: { ...(current[criterion.key] ?? { score: "", comment: "" }), score: event.target.value } }))} disabled={packet.status === "SUBMITTED"} /></div>
                        <div className="space-y-2"><Label htmlFor={`comment-${criterion.key}`}>Criterion comment {criterion.require_comment ? "(required)" : "(optional)"}</Label><Textarea id={`comment-${criterion.key}`} rows={2} value={scoreDraft[criterion.key]?.comment ?? ""} onChange={(event) => setScoreDraft((current) => ({ ...current, [criterion.key]: { ...(current[criterion.key] ?? { score: "", comment: "" }), comment: event.target.value } }))} disabled={packet.status === "SUBMITTED"} placeholder="Evidence-based rationale" /></div>
                      </div>
                    </div>
                  ))}
                  <div className="space-y-2"><Label htmlFor="evaluator-comments">Overall feedback</Label><Textarea id="evaluator-comments" rows={3} value={evaluatorComments} onChange={(event) => setEvaluatorComments(event.target.value)} disabled={packet.status === "SUBMITTED"} maxLength={10000} placeholder="Summarize strengths, gaps, and actionable feedback." /></div>
                  <div className="flex flex-wrap justify-end gap-2">
                    <Button variant="outline" disabled={busy || packet.status === "SUBMITTED"} onClick={() => void saveScorePacket(false)}>Save draft</Button>
                    <Button disabled={busy || packet.status === "SUBMITTED"} onClick={() => void saveScorePacket(true)}><Send className="mr-2 size-4" />{busy ? "Submitting…" : "Submit assessment"}</Button>
                  </div>
                </CardContent>
              </Card>}
          </section>
        </div>

        <section className="space-y-3">
          <div><h2 className="text-lg font-semibold tracking-tight">Supervised student performance</h2><p className="mt-1 text-sm text-muted-foreground">Student identity and published results are available here only for placements you supervise. Blind evaluator assignments remain separate.</p></div>
          <Card className="rounded-xl border-border/80 shadow-none">
            <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
              <div className="min-w-0 flex-1 space-y-2">
                <Label htmlFor="supervised-student">Supervised student</Label>
                <Select value={selectedSupervisedStudentId} onValueChange={(value) => { setSelectedSupervisedStudentId(value ?? ""); setSupervisedResults([]); setSupervisedResultError(""); }}>
                  <SelectTrigger id="supervised-student" className="w-full"><SelectValue placeholder="Select a supervised student" /></SelectTrigger>
                  <SelectContent>
                    {supervisedStudents.map((student) => <SelectItem key={student.student_profile_id} value={String(student.student_profile_id)}>{student.full_name} · {student.enrollment_number}</SelectItem>)}
                  </SelectContent>
                </Select>
                {supervisedStudents.length === 0 && <p className="text-xs text-muted-foreground">No supervised student placements were returned for your faculty profile.</p>}
              </div>
              <Button variant="outline" disabled={!selectedSupervisedStudentId || supervisedResultLoading} onClick={() => void loadSupervisedResults()}>{supervisedResultLoading ? "Loading…" : "View published results"}</Button>
            </CardContent>
          </Card>
          {supervisedResultError && <StateAlert title="Student results unavailable" message={supervisedResultError} />}
          {selectedSupervisedStudentId && !supervisedResultLoading && supervisedResults.length === 0 && !supervisedResultError && <Card className="border-dashed shadow-none"><CardContent className="py-7 text-center"><Activity className="mx-auto size-7 text-muted-foreground" /><p className="mt-2 font-medium">No published outcomes</p><p className="mt-1 text-sm text-muted-foreground">Only published results from placements you supervise appear here.</p></CardContent></Card>}
          {supervisedResults.length > 0 && (
            <Card className="rounded-xl border-border/80 shadow-none">
              <CardHeader><CardTitle className="text-base">Published internship results</CardTitle><CardDescription>Persisted academic records only. Scores are shown on a 0–100 scale.</CardDescription></CardHeader>
              <CardContent>
                {supervisedResults.length >= 2 ? <div className="h-60 w-full" role="img" aria-label="Line chart of published internship assessment scores for the selected supervised student"><ResponsiveContainer width="100%" height="100%"><LineChart data={supervisedResults.map((item, index) => ({ period: `Sem ${item.semester} · ${index + 1}`, score: item.total_score }))} margin={{ top: 8, right: 12, left: -16, bottom: 6 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="period" tickLine={false} axisLine={false} /><YAxis domain={[0, 100]} tickLine={false} axisLine={false} width={38} /><Tooltip formatter={(value) => [`${value} / 100`, "Score"]} /><Line type="monotone" dataKey="score" stroke="var(--color-primary)" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 5 }} /></LineChart></ResponsiveContainer></div> : <p className="mb-4 rounded-lg border border-border bg-muted/20 p-3 text-sm text-muted-foreground">One published result is available; a trend chart appears after a second result is recorded.</p>}
                <div className="overflow-x-auto rounded-lg border border-border"><table className="w-full min-w-[480px] text-left text-sm"><thead className="bg-muted/50 text-xs text-muted-foreground"><tr><th className="px-4 py-3 font-medium">Assessment</th><th className="px-4 py-3 font-medium">Semester</th><th className="px-4 py-3 font-medium">Score</th><th className="px-4 py-3 font-medium">Grade</th></tr></thead><tbody>{supervisedResults.map((result) => <tr key={result.id} className="border-t border-border"><td className="px-4 py-3 font-medium">{result.title || "Internship assessment"}</td><td className="px-4 py-3">Semester {result.semester}</td><td className="px-4 py-3 tabular-nums">{result.total_score.toFixed(2)} / 100</td><td className="px-4 py-3"><Badge variant="outline">{result.grade}</Badge></td></tr>)}</tbody></table></div>
              </CardContent>
            </Card>
          )}
        </section>
        </div>
      )}
    </main>
  );
}

function GraduationCapIcon() {
  return <ClipboardCheck className="mx-auto size-8 text-muted-foreground" aria-hidden="true" />;
}
