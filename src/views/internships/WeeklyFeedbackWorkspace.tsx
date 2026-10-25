import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, MessageSquareText, RefreshCw, Save, Send } from "lucide-react";
import { apiRequest, ApiError } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

type Participation = { id: number; title?: string | null; company_name?: string; starts_on: string; ends_on?: string | null; status: string };
type Feedback = { id: number; participation_id: number; week_start: string; reviewer_type: string; reviewer_account_id: number | null; industry_mentor_id: number | null; overall_rating: number | null; attendance_rating: number | null; technical_rating: number | null; communication_rating: number | null; strengths?: string | null; improvement_areas?: string | null; feedback_text?: string | null; status: string; submitted_at?: string | null; created_at?: string; updated_at?: string };
type Payload = { overall_rating: number | null; attendance_rating: number | null; technical_rating: number | null; communication_rating: number | null; strengths: string; improvement_areas: string; feedback_text: string };
const now = new Date();
const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const monday = (value: string) => { const d = new Date(`${value.slice(0, 10)}T12:00:00`); d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); return iso(d); };
const showDate = (value?: string | null) => value ? new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "Not recorded";
const label = (value: string) => value.replace(/_/g, " ").replace(/^./, (v) => v.toUpperCase());
const variant = (value: string): "default" | "secondary" | "outline" | "destructive" => value === "submitted" ? "secondary" : value === "locked" ? "destructive" : value === "returned" ? "outline" : "default";
const errorText = (error: unknown) => error instanceof ApiError ? error.message : "Kairos could not be reached. Check your connection and retry.";
const blank = (): Payload => ({ overall_rating: null, attendance_rating: null, technical_rating: null, communication_rating: null, strengths: "", improvement_areas: "", feedback_text: "" });
const names: Record<string, string> = { student_self: "Student self-reflection", faculty_mentor: "Faculty mentor feedback", industry_mentor: "Industry mentor feedback" };

export default function WeeklyFeedbackWorkspace() {
  const { account } = useAuth();
  const [participations, setParticipations] = useState<Participation[]>([]);
  const [reviewerType, setReviewerType] = useState("student_self");
  const [participationId, setParticipationId] = useState("");
  const [weekStart, setWeekStart] = useState("");
  const [items, setItems] = useState<Feedback[]>([]);
  const [form, setForm] = useState<Payload>(blank());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selected = participations.find((p) => String(p.id) === participationId);
  const weeks = useMemo(() => {
    if (!selected) return [];
    const start = monday(selected.starts_on);
    const last = selected.ends_on && selected.ends_on < iso(now) ? selected.ends_on : iso(now);
    const end = monday(last);
    const result: string[] = [];
    for (const d = new Date(`${start}T12:00:00`); iso(d) <= end; d.setDate(d.getDate() + 7)) result.push(iso(d));
    return result;
  }, [selected?.id, selected?.starts_on, selected?.ends_on]);
  const own = items.find((item) => item.reviewer_type === reviewerType);
  const editable = !own || own.status === "draft" || own.status === "returned";

  const loadParticipations = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const response = await apiRequest<{ items: Participation[]; reviewer_type: string }>("/internship-feedback/participations");
      setParticipations(response.items || []);
      setReviewerType(response.reviewer_type);
      setParticipationId((current) => current && response.items.some((p) => String(p.id) === current) ? current : String(response.items[0]?.id ?? ""));
    } catch (e) { setError(errorText(e)); }
    finally { setLoading(false); }
  }, []);
  const loadWeek = useCallback(async () => {
    if (!participationId || !weekStart) { setItems([]); return; }
    setError(null);
    try {
      const response = await apiRequest<{ items: Feedback[] }>(`/internship-feedback/participations/${encodeURIComponent(participationId)}?week_start=${encodeURIComponent(weekStart)}`);
      setItems(response.items || []);
      const record = (response.items || []).find((item) => item.reviewer_type === reviewerType);
      setForm(record ? { overall_rating: record.overall_rating, attendance_rating: record.attendance_rating, technical_rating: record.technical_rating, communication_rating: record.communication_rating, strengths: record.strengths || "", improvement_areas: record.improvement_areas || "", feedback_text: record.feedback_text || "" } : blank());
    } catch (e) { setError(errorText(e)); }
  }, [participationId, weekStart, reviewerType]);
  useEffect(() => { void loadParticipations(); }, [loadParticipations]);
  useEffect(() => {
    if (!weeks.length) { setWeekStart(""); return; }
    setWeekStart((current) => current && weeks.includes(current) ? current : weeks[weeks.length - 1]);
  }, [participationId, weeks]);
  useEffect(() => { void loadWeek(); }, [loadWeek]);
  const change = (key: keyof Payload, value: string) => setForm((old) => ({ ...old, [key]: ["overall_rating", "attendance_rating", "technical_rating", "communication_rating"].includes(key) ? (value === "" ? null : Number(value)) : value }));
  const save = async (submit: boolean) => {
    if (!participationId || !weekStart || saving || !editable) return;
    setSaving(true); setError(null);
    try {
      const saved = await apiRequest<Feedback>(`/internship-feedback/participations/${encodeURIComponent(participationId)}/weeks/${encodeURIComponent(weekStart)}`, { method: "PUT", body: JSON.stringify(form) });
      if (submit) {
        const submitted = await apiRequest<Feedback>(`/internship-feedback/participations/${encodeURIComponent(participationId)}/weeks/${encodeURIComponent(weekStart)}/submit`, { method: "POST" });
        setItems((old) => [...old.filter((item) => item.id !== submitted.id), submitted]);
        toast.success("Weekly feedback submitted.");
      } else {
        setItems((old) => [...old.filter((item) => item.id !== saved.id), saved]);
        toast.success("Draft saved.");
      }
      await loadWeek();
    } catch (e) { setError(errorText(e)); toast.error(errorText(e)); }
    finally { setSaving(false); }
  };
  if (loading) return <div className="space-y-4"><Skeleton className="h-24 w-full" /><Skeleton className="h-52 w-full" /></div>;
  if (error && !participations.length) return <Alert variant="destructive"><AlertCircle className="size-4" /><AlertTitle>Feedback unavailable</AlertTitle><AlertDescription>{error}<Button className="mt-3" variant="outline" size="sm" onClick={() => void loadParticipations()}><RefreshCw className="mr-2 size-4" />Retry</Button></AlertDescription></Alert>;

  return <div className="space-y-5">
    {error && <Alert variant="destructive"><AlertCircle className="size-4" /><AlertTitle>Request failed</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
    {!participations.length ? <Card><CardContent className="py-12 text-center"><MessageSquareText className="mx-auto mb-3 size-8 text-muted-foreground" /><h2 className="font-semibold">No internship participation found</h2><p className="mt-2 text-sm text-muted-foreground">Feedback becomes available after a participation is recorded and assigned to your account.</p></CardContent></Card> : <>
      <Card><CardHeader><CardTitle>Weekly feedback workspace</CardTitle><CardDescription>Saved records are loaded from Kairos and are scoped to your internship permissions.</CardDescription></CardHeader><CardContent className="grid gap-4 md:grid-cols-3">
        <div className="grid gap-2"><Label>Internship</Label><Select value={participationId} onValueChange={(value) => setParticipationId(value || "")}><SelectTrigger><SelectValue placeholder="Choose internship" /></SelectTrigger><SelectContent>{participations.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.title || `Participation #${p.id}`}</SelectItem>)}</SelectContent></Select></div>
        <div className="grid gap-2"><Label>Organization</Label><div className="flex h-10 items-center rounded-md border px-3 text-sm">{selected?.company_name || "Not specified"}</div></div>
        <div className="grid gap-2"><Label>Feedback week</Label><Select value={weekStart} onValueChange={(value) => setWeekStart(value || "")}><SelectTrigger><SelectValue placeholder="Choose week" /></SelectTrigger><SelectContent>{weeks.map((week) => { const end = new Date(`${week}T12:00:00`); end.setDate(end.getDate() + 6); return <SelectItem key={week} value={week}>{showDate(week)} – {showDate(iso(end))}</SelectItem>; })}</SelectContent></Select></div>
        <div className="md:col-span-3 flex flex-wrap items-center gap-2 text-sm text-muted-foreground"><span>Internship dates: {showDate(selected?.starts_on)} – {showDate(selected?.ends_on)}</span><span>·</span><span>Status <Badge variant="outline">{selected?.status || "unknown"}</Badge></span><span>·</span><span>Signed in as {account?.full_name || "current account"}</span></div>
      </CardContent></Card>
      <div className="grid gap-4 lg:grid-cols-3">{(["student_self", "faculty_mentor", "industry_mentor"] as const).map((type) => {
        const record = items.find((item) => item.reviewer_type === type);
        return <Card key={type} className="min-w-0"><CardHeader><div className="flex items-start justify-between gap-2"><CardTitle className="text-base">{names[type]}</CardTitle><Badge variant={record ? variant(record.status) : "outline"}>{record ? label(record.status) : "Not submitted"}</Badge></div><CardDescription>{record ? `Week of ${showDate(record.week_start)} · Updated ${showDate(record.updated_at)}` : "No feedback record for this week."}</CardDescription></CardHeader><CardContent className="space-y-3 text-sm">
          {record ? <><div className="grid grid-cols-2 gap-2">{[["Overall", record.overall_rating], ["Attendance", record.attendance_rating], ["Technical", record.technical_rating], ["Communication", record.communication_rating]].map(([title, rating]) => <div key={String(title)} className="rounded-md bg-muted/50 p-2"><p className="text-xs text-muted-foreground">{title}</p><p className="mt-1 font-semibold">{rating == null ? "—" : `${rating}/5`}</p></div>)}</div>{record.strengths && <p><span className="font-medium">Strengths: </span>{record.strengths}</p>}{record.improvement_areas && <p><span className="font-medium">Improvement: </span>{record.improvement_areas}</p>}{record.feedback_text && <p className="whitespace-pre-wrap">{record.feedback_text}</p>}{record.submitted_at && <p className="text-xs text-muted-foreground">Submitted {showDate(record.submitted_at)}</p>}{reviewerType === "faculty_mentor" && type === "student_self" && record.status === "submitted" && <div className="flex flex-wrap gap-2 pt-2"><Button size="sm" variant="outline" disabled={transitionBusy} onClick={async () => { setTransitionBusy(true); try { const saved = await apiRequest<Feedback>(`/internship-feedback/participations/${participationId}/weeks/${weekStart}/records/${record.id}/return`, { method: "POST" }); setItems((old) => old.map((item) => item.id === saved.id ? saved : item)); toast.success("Student reflection returned for correction."); } catch (e) { toast.error(errorText(e)); } finally { setTransitionBusy(false); } }}>Return for correction</Button><Button size="sm" disabled={transitionBusy} onClick={async () => { setTransitionBusy(true); try { const saved = await apiRequest<Feedback>(`/internship-feedback/participations/${participationId}/weeks/${weekStart}/records/${record.id}/lock`, { method: "POST" }); setItems((old) => old.map((item) => item.id === saved.id ? saved : item)); toast.success("Student reflection locked."); } catch (e) { toast.error(errorText(e)); } finally { setTransitionBusy(false); } }}>Lock feedback</Button></div>}</> : <p className="text-muted-foreground">No saved feedback for this reviewer and week.</p>}
        </CardContent></Card>;
      })}</div>
      <Card><CardHeader><CardTitle>{own ? `Your ${label(own.status).toLowerCase()} feedback` : "Add your weekly feedback"}</CardTitle><CardDescription>{editable ? "Save a draft to continue later, or submit when ready." : "Submitted and locked feedback is read-only. Returned feedback can be corrected."}</CardDescription></CardHeader><CardContent>
        {!editable ? <Alert><CheckCircle2 className="size-4" /><AlertTitle>Feedback is read-only</AlertTitle><AlertDescription>This record cannot be edited in its current state.</AlertDescription></Alert> : <form className="grid gap-4" onSubmit={(event) => { event.preventDefault(); void save(false); }}>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{([["overall_rating", "Overall experience (0–5)", 0, 5], ["attendance_rating", "Attendance (1–5)", 1, 5], ["technical_rating", "Technical learning (1–5)", 1, 5], ["communication_rating", "Communication (1–5)", 1, 5]] as const).map(([key, title, min, max]) => <div className="grid gap-2" key={key}><Label htmlFor={key}>{title}</Label><Input id={key} type="number" min={min} max={max} step={key === "overall_rating" ? "0.5" : "1"} value={form[key] ?? ""} onChange={(event) => change(key, event.target.value)} /></div>)}</div>
          <div className="grid gap-2"><Label htmlFor="strengths">Strengths and accomplishments</Label><Textarea id="strengths" maxLength={10000} value={form.strengths} onChange={(event) => change("strengths", event.target.value)} /></div>
          <div className="grid gap-2"><Label htmlFor="improvement-areas">Areas for improvement</Label><Textarea id="improvement-areas" maxLength={10000} value={form.improvement_areas} onChange={(event) => change("improvement_areas", event.target.value)} /></div>
          <div className="grid gap-2"><Label htmlFor="feedback-text">Weekly reflection / feedback</Label><Textarea id="feedback-text" maxLength={20000} value={form.feedback_text} onChange={(event) => change("feedback_text", event.target.value)} /></div>
          <div className="flex flex-wrap gap-2"><Button type="submit" variant="outline" disabled={saving || !weekStart}><Save className="mr-2 size-4" />{saving ? "Saving…" : "Save draft"}</Button><Button type="button" disabled={saving || !weekStart} onClick={() => void save(true)}><Send className="mr-2 size-4" />{saving ? "Saving…" : own?.status === "returned" ? "Resubmit feedback" : "Submit feedback"}</Button><Button type="button" variant="ghost" disabled={saving} onClick={() => void loadWeek()}><RefreshCw className="mr-2 size-4" />Reload</Button></div>
        </form>}
      </CardContent></Card>
    </>}
  </div>;
}
