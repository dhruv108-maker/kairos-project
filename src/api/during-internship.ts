import { apiRequest, getAccessToken } from "@/api/kairos-client";

export type PlacementStatus = "ONGOING" | "COMPLETED" | "TERMINATED";
export type WorkLogStatus = "DRAFT" | "SUBMITTED";
export type WorkLogDecision = "COMMENTED" | "APPROVED" | "REVISION_REQUIRED";
export type ReviewRole = "FACULTY" | "INDUSTRY_MENTOR";
export type ReportStatus = "DRAFT" | "SUBMITTED" | "UNDER_EVALUATION" | "REVISION_REQUIRED" | "APPROVED" | "REJECTED";

export interface Placement {
  id: string;
  application_id: string;
  student: { id: string; name: string; enrollment_number: string | null };
  opportunity: { id: string; title: string; company_name: string | null; location: string | null };
  faculty_supervisor_id: string | null;
  faculty_supervisor_name: string | null;
  industry_mentor_account_id: string | null;
  industry_mentor_name: string | null;
  start_date: string;
  end_date: string;
  status: PlacementStatus;
  created_at: string | null;
  updated_at: string | null;
}

export interface WorkLogReview {
  id: string;
  reviewer_account_id: string;
  reviewer_name: string | null;
  reviewer_role: ReviewRole;
  decision: WorkLogDecision;
  feedback: string;
  created_at: string | null;
}

export interface WorkLog {
  id: string;
  placement_id: string;
  student_id: string;
  work_date: string;
  duration_minutes: number | null;
  work_summary: string;
  tasks_completed: string | null;
  skills_used: string[];
  challenges: string | null;
  learning_outcomes: string | null;
  next_steps: string | null;
  status: WorkLogStatus;
  submitted_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  latest_reviews: WorkLogReview[];
  reviews: WorkLogReview[];
}

export interface ReportSubmission {
  id: string;
  placement_id: string;
  requirement_id: string | null;
  title: string;
  latest_version_number: number;
  status: ReportStatus;
  review_feedback: string | null;
  reviewed_by_account_id: string | null;
  reviewed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ReportVersion {
  id: string;
  submission_id: string;
  version_number: number;
  file_id: string;
  submission_notes: string | null;
  submitted_at: string | null;
}

export interface GriffinEvaluation {
  id: string;
  report_version_id: string;
  griffin_project_id: string;
  griffin_report_id: string;
  griffin_job_id: string | null;
  current_status: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED" | "RETRIED";
  created_at: string | null;
  updated_at: string | null;
}

interface Items<T> { items: T[] }
interface UploadFileResponse { id: string; original_name: string; file_size_bytes: number; mime_type: string; sha256_hash: string; created_at: string }

const base = "/modules/internships";

export const duringInternshipApi = {
  studentPlacements: () => apiRequest<Items<Placement>>(base + "/placements/me"),
  supervisedPlacements: () => apiRequest<Items<Placement>>(base + "/placements/supervised"),
  mentorPlacements: () => apiRequest<Items<Placement>>(base + "/placements/industry-mentor"),
  workLogsMine: () => apiRequest<Items<WorkLog>>(base + "/work-logs/me"),
  workLogsForPlacement: (placementId: string) =>
    apiRequest<Items<WorkLog>>(base + "/placements/" + encodeURIComponent(placementId) + "/work-logs"),
  createWorkLog: (placementId: string, payload: {
    work_date: string; work_summary: string; duration_minutes: number | null; tasks_completed: string | null;
    skills_used: string[]; challenges: string | null; learning_outcomes: string | null; next_steps: string | null;
  }) =>
    apiRequest<WorkLog>(base + "/placements/" + encodeURIComponent(placementId) + "/work-logs", {
      method: "POST", body: JSON.stringify(payload),
    }),
  updateWorkLog: (workLogId: string, payload: Partial<Pick<WorkLog, "work_date" | "duration_minutes" | "work_summary" | "tasks_completed" | "skills_used" | "challenges" | "learning_outcomes" | "next_steps">>) =>
    apiRequest<WorkLog>(base + "/work-logs/" + encodeURIComponent(workLogId), {
      method: "PATCH", body: JSON.stringify(payload),
    }),
  submitWorkLog: (workLogId: string) =>
    apiRequest<WorkLog>(base + "/work-logs/" + encodeURIComponent(workLogId) + "/submit", { method: "POST" }),
  reviewWorkLog: (workLogId: string, decision: WorkLogDecision, feedback: string) =>
    apiRequest<WorkLogReview>(base + "/work-logs/" + encodeURIComponent(workLogId) + "/reviews", {
      method: "POST", body: JSON.stringify({ decision, feedback }),
    }),
  assignIndustryMentor: (placementId: string, accountId: string) =>
    apiRequest<{ placement_id: string; industry_mentor_account_id: string; industry_mentor_name: string }>(
      base + "/placements/" + encodeURIComponent(placementId) + "/industry-mentor",
      { method: "POST", body: JSON.stringify({ account_id: accountId }) },
    ),
  myReports: () => apiRequest<Items<ReportSubmission>>("/reports/me"),
  supervisedReports: () => apiRequest<Items<ReportSubmission>>("/reports/supervised"),
  reportVersions: (submissionId: string) =>
    apiRequest<Items<ReportVersion>>("/reports/" + encodeURIComponent(submissionId) + "/versions"),
  createReport: (placementId: string, title: string, fileId: string, submissionNotes: string) =>
    apiRequest<ReportSubmission>("/reports", {
      method: "POST",
      body: JSON.stringify({ placement_id: placementId, title, file_id: fileId, submission_notes: submissionNotes || null }),
    }),
  addReportVersion: (submissionId: string, fileId: string, submissionNotes: string) =>
    apiRequest<ReportVersion>("/reports/" + encodeURIComponent(submissionId) + "/versions", {
      method: "POST", body: JSON.stringify({ file_id: fileId, submission_notes: submissionNotes || null }),
    }),
  submitReport: (submissionId: string) =>
    apiRequest<ReportSubmission>("/reports/" + encodeURIComponent(submissionId) + "/submit", { method: "POST" }),
  reviewReport: (submissionId: string, status: Exclude<ReportStatus, "DRAFT" | "SUBMITTED">, feedbackComments: string) =>
    apiRequest<ReportSubmission>("/reports/" + encodeURIComponent(submissionId) + "/status", {
      method: "PATCH", body: JSON.stringify({ status, feedback_comments: feedbackComments || null }),
    }),
  evaluationForVersion: (versionId: string) =>
    apiRequest<{ item: GriffinEvaluation | null }>("/evaluations/report-versions/" + encodeURIComponent(versionId)),
  requestEvaluation: (versionId: string, projectId: string, reportId: string) =>
    apiRequest<GriffinEvaluation>("/evaluations/report-versions/" + encodeURIComponent(versionId), {
      method: "POST", body: JSON.stringify({ griffin_project_id: projectId, griffin_report_id: reportId }),
    }),
  evaluationAttempts: (evaluationId: string) =>
    apiRequest<{ items: Array<{ id: string; attempt_number: number; execution_status: string; error_message: string | null; started_at: string | null; completed_at: string | null }> }>("/evaluations/" + encodeURIComponent(evaluationId) + "/attempts"),
  uploadFile: async (file: File): Promise<UploadFileResponse> => {
    const body = new FormData();
    body.append("file", file);
    return apiRequest<UploadFileResponse>("/storage/upload", { method: "POST", body });
  },
  downloadFile: async (fileId: string): Promise<{ blob: Blob; filename: string }> => {
    const apiBase = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/+$/, "");
    const response = await fetch(apiBase + "/storage/" + encodeURIComponent(fileId), {
      headers: (() => {
        const token = getAccessToken();
        return token ? { Authorization: "Bearer " + token } : {};
      })(),
    });
    if (!response.ok) {
      let message = "File download failed (" + response.status + ")";
      try {
        const body = await response.json() as { detail?: string };
        if (body.detail) message = body.detail;
      } catch { /* response was not JSON */ }
      throw new Error(message);
    }
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/i);
    return { blob: await response.blob(), filename: match?.[1] || "report-" + fileId };
  },
};
