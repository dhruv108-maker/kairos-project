import { useCallback, useEffect, useState } from "react";
import { AlertCircle, ClipboardCheck, RefreshCw, ShieldCheck } from "lucide-react";
import { apiRequest, ApiError } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

type Criterion = { id: string; code: string; title: string; description: string; minimum_score: string; maximum_score: string; weight: string; position: number };
type Score = { criterion_id: string; score: string; feedback: string | null };
type Assignment = { id: string; status: "DRAFT" | "SUBMITTED" | "RELEASED"; submitted_at: string | null; report_version_id: string; evidence: { report_file_id: string; presentation_file_id: string | null }; rubric: { id: string; name: string; version_number: number }; criteria: Criterion[]; scores: Score[] };
type Value = { score: string; feedback: string };

export default function BlindAssessmentPage() {
  const { account } = useAuth();
  const [items, setItems] = useState<Assignment[]>([]);
  const [values, setValues] = useState<Record<string, Record<string, Value>>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<{ items: Assignment[] }>("/blind-assessments/me");
      const next = response.items ?? [];
      setItems(next);
      setValues((current) => {
        const result = { ...current };
        for (const assignment of next) {
          const draft = { ...(result[assignment.id] ?? {}) };
          for (const criterion of assignment.criteria) {
            const stored = assignment.scores.find((score) => score.criterion_id === criterion.id);
            if (!draft[criterion.id]) draft[criterion.id] = { score: stored?.score ?? "", feedback: stored?.feedback ?? "" };
          }
          result[assignment.id] = draft;
        }
        return result;
      });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : cause instanceof Error ? cause.message : "Assigned assessments could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const update = (assignmentId: string, criterionId: string, field: keyof Value, value: string) => {
    setValues((current) => ({ ...current, [assignmentId]: { ...(current[assignmentId] ?? {}), [criterionId]: { ...(current[assignmentId]?.[criterionId] ?? { score: "", feedback: "" }), [field]: value } } }));
  };
  const save = async (assignment: Assignment, submit: boolean) => {
    const scores = assignment.criteria.map((criterion) => {
      const value = values[assignment.id]?.[criterion.id] ?? { score: "", feedback: "" };
      return { criterion_id: criterion.id, score: value.score, feedback: value.feedback.trim() || null };
    });
    if (scores.some((score) => score.score.trim() === "" || !Number.isFinite(Number(score.score)))) {
      setError("Enter a numeric score for every criterion before saving or submitting.");
      return;
    }
    setSaving(assignment.id); setError(""); setNotice("");
    try {
      await apiRequest("/blind-assessments/assignments/" + encodeURIComponent(assignment.id) + "/scores", {
        method: "PUT",
        body: JSON.stringify({ scores: scores.map((score) => ({ ...score, score: Number(score.score) })), submit }),
      });
      setNotice(submit ? "Assessment submitted. Its scores are now locked." : "Draft scores saved.");
      await load();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : cause instanceof Error ? cause.message : "Scores could not be saved.");
    } finally { setSaving(""); }
  };

  if (!account?.roles.some((role) => role.toUpperCase() === "FACULTY")) {
    return <main className="mx-auto max-w-4xl p-6"><Card><CardHeader><CardTitle>Faculty access required</CardTitle><CardDescription>This workspace is restricted to authenticated faculty.</CardDescription></CardHeader></Card></main>;
  }

  return <main className="mx-auto w-full max-w-6xl space-y-6 pb-10">
    <header className="flex flex-col justify-between gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end">
      <div><div className="flex items-center gap-2 text-sm font-medium text-primary"><ShieldCheck className="h-4 w-4" /> Independent assessment</div><h1 className="mt-2 text-3xl font-semibold tracking-tight">Blind assessment inbox</h1><p className="mt-2 max-w-2xl text-sm text-muted-foreground">Only assignments explicitly made to your account appear here. Student identity and profile details are omitted from the packet response.</p></div>
      <Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
    </header>
    {error && <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Could not complete request</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
    {notice && <Alert><ClipboardCheck className="h-4 w-4" /><AlertTitle>Assessment updated</AlertTitle><AlertDescription>{notice}</AlertDescription></Alert>}
    {loading ? <div className="space-y-4">{[0, 1].map((key) => <Card key={key}><CardHeader><Skeleton className="h-6 w-56" /><Skeleton className="h-4 w-80" /></CardHeader><CardContent><Skeleton className="h-28 w-full" /></CardContent></Card>)}</div> :
      items.length === 0 ? <Card><CardContent className="flex flex-col items-center gap-2 py-14 text-center"><ClipboardCheck className="h-8 w-8 text-muted-foreground" /><h2 className="text-lg font-semibold">No blind assessments assigned</h2><p className="max-w-lg text-sm text-muted-foreground">An authorized academic administrator must assign a submitted report version and approved rubric before it appears here.</p></CardContent></Card> :
      <div className="space-y-5">{items.map((assignment) => {
        const locked = assignment.status !== "DRAFT";
        return <Card key={assignment.id} className="shadow-none">
          <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between"><div><CardTitle>{assignment.rubric?.name ?? "Assigned rubric"} · v{assignment.rubric?.version_number}</CardTitle><CardDescription className="mt-1">Version reference: {assignment.report_version_id}</CardDescription><p className="mt-2 text-xs text-muted-foreground">Evidence: <a className="underline underline-offset-4" href={"/api/v1/storage/" + encodeURIComponent(assignment.evidence.report_file_id)}>Report PDF</a>{assignment.evidence.presentation_file_id && <> · <a className="underline underline-offset-4" href={"/api/v1/storage/" + encodeURIComponent(assignment.evidence.presentation_file_id)}>Presentation PDF</a></>}</p></div><Badge variant={locked ? "secondary" : "outline"}>{assignment.status}</Badge></CardHeader>
          <CardContent className="space-y-5">{assignment.criteria.map((criterion) => {
            const value = values[assignment.id]?.[criterion.id] ?? { score: "", feedback: "" };
            const inputId = "score-" + assignment.id + "-" + criterion.id;
            return <section key={criterion.id} className="grid gap-3 border-t border-border pt-4 md:grid-cols-[minmax(0,1fr)_9rem]">
              <div><div className="font-medium">{criterion.position + 1}. {criterion.title} <span className="text-xs text-muted-foreground">({criterion.code})</span></div><p className="mt-1 text-sm text-muted-foreground">{criterion.description}</p><p className="mt-2 text-xs text-muted-foreground">Allowed score: {criterion.minimum_score}–{criterion.maximum_score} · Weight: {criterion.weight}</p><Textarea className="mt-3" rows={2} placeholder="Criterion feedback (optional)" value={value.feedback} disabled={locked || saving === assignment.id} onChange={(event) => update(assignment.id, criterion.id, "feedback", event.target.value)} /></div>
              <div><label className="text-sm font-medium" htmlFor={inputId}>Score</label><Input id={inputId} className="mt-2" type="number" min={criterion.minimum_score} max={criterion.maximum_score} step="0.01" value={value.score} disabled={locked || saving === assignment.id} onChange={(event) => update(assignment.id, criterion.id, "score", event.target.value)} /></div>
            </section>;
          })}
          {!locked && <div className="flex flex-wrap justify-end gap-2 border-t border-border pt-4"><Button variant="outline" disabled={saving === assignment.id} onClick={() => void save(assignment, false)}>{saving === assignment.id ? "Saving…" : "Save draft"}</Button><Button disabled={saving === assignment.id} onClick={() => void save(assignment, true)}>{saving === assignment.id ? "Submitting…" : "Submit assessment"}</Button></div>}
          {locked && <p className="text-sm text-muted-foreground">This assessment is submitted and locked. Only an authorized administrator can reopen it.</p>}
          </CardContent>
        </Card>;
      })}</div>}
  </main>;
}
