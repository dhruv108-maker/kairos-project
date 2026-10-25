import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AlertCircle, BookOpenCheck, Plus, RefreshCw, Save, ShieldCheck, Trash2 } from "lucide-react";
import { apiRequest, ApiError } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";

type Institution = { id: string; name: string; slug: string; status: string };
type Programme = { id: string; name: string; code?: string | null; status?: string };
type Criterion = { key: string; label: string; description: string; max_score: string; require_comment: boolean };
type GradeBand = { grade: string; min_score: string; max_score: string };
type Policy = {
  id: string; institution_id: string; programme_id: string; version: number; name: string;
  criteria: Array<{ key: string; label: string; description: string; max_score: number; require_comment: boolean }>;
  component_weights: Record<string, number>; griffin_score_max: number;
  curriculum_status_scores: { MAPPED: number; PARTIALLY_MAPPED: number; NOT_EVIDENCED: number };
  grade_bands: Array<{ grade: string; min_score: number; max_score: number }>;
  passing_score: number; final_approver_role: string; required_evaluator_count: number;
  show_curriculum_mapping_to_evaluator: boolean; is_active: boolean; created_at: string;
};
type Outcome = {
  id: string; institution_id: string; programme_id: string; semester: number; outcome_code: string;
  title: string; expected_competency: string; source_reference: string; is_active: boolean;
};
type ItemList<T> = { items: T[] };
const readableError = (cause: unknown) => {
  if (cause instanceof ApiError) {
    if (cause.status === 401) return "Your session has expired. Sign in again.";
    if (cause.status === 403) return "Only an active institution administrator for this institution can manage assessment configuration.";
    if (cause.status === 409) return cause.message;
    return cause.message;
  }
  return cause instanceof Error ? cause.message : "Kairos could not complete the request. Retry and check your connection.";
};
const numberText = (value: string) => value.trim() !== "" && Number.isFinite(Number(value));

export default function InternshipAssessmentPolicyPage() {
  const { account } = useAuth();
  const isInstitutionAdmin = account?.roles.some((role) => role.toUpperCase() === "INSTITUTION_ADMIN") ?? false;
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [institutionId, setInstitutionId] = useState("");
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [programmeId, setProgrammeId] = useState("");
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [outcomes, setOutcomes] = useState<Outcome[]>([]);
  const [semester, setSemester] = useState("1");
  const [loading, setLoading] = useState(true);
  const [catalogueLoading, setCatalogueLoading] = useState(false);
  const [savingPolicy, setSavingPolicy] = useState(false);
  const [savingOutcome, setSavingOutcome] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [policyName, setPolicyName] = useState("");
  const [criteria, setCriteria] = useState<Criterion[]>([]);
  const [weights, setWeights] = useState({ griffin: "", curriculum: "", faculty: "" });
  const [griffinScoreMax, setGriffinScoreMax] = useState("");
  const [curriculumScores, setCurriculumScores] = useState({ MAPPED: "", PARTIALLY_MAPPED: "", NOT_EVIDENCED: "" });
  const [gradeBands, setGradeBands] = useState<GradeBand[]>([]);
  const [passingScore, setPassingScore] = useState("");
  const [finalApproverRole, setFinalApproverRole] = useState("");
  const [requiredEvaluators, setRequiredEvaluators] = useState("");
  const [showMappingToEvaluator, setShowMappingToEvaluator] = useState(false);

  const [outcomeCode, setOutcomeCode] = useState("");
  const [outcomeTitle, setOutcomeTitle] = useState("");
  const [outcomeCompetency, setOutcomeCompetency] = useState("");
  const [outcomeSource, setOutcomeSource] = useState("");

  const loadInstitutions = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<ItemList<Institution>>("/institutions");
      const list = response.items ?? [];
      setInstitutions(list);
      setInstitutionId((current) => current && list.some((item) => item.id === current) ? current : list[0]?.id ?? "");
    } catch (cause) {
      setError(readableError(cause));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (isInstitutionAdmin) void loadInstitutions(); }, [isInstitutionAdmin, loadInstitutions]);

  const loadProgrammes = useCallback(async () => {
    if (!institutionId) {
      setProgrammes([]);
      setProgrammeId("");
      return;
    }
    setCatalogueLoading(true);
    setError("");
    try {
      const response = await apiRequest<ItemList<Programme>>(`/institutions/${encodeURIComponent(institutionId)}/programmes`);
      const list = (response.items ?? []).filter((item) => !item.status || item.status.toUpperCase() === "ACTIVE");
      setProgrammes(list);
      setProgrammeId((current) => current && list.some((item) => item.id === current) ? current : list[0]?.id ?? "");
    } catch (cause) {
      setProgrammes([]);
      setProgrammeId("");
      setError(readableError(cause));
    } finally {
      setCatalogueLoading(false);
    }
  }, [institutionId]);
  useEffect(() => { void loadProgrammes(); }, [loadProgrammes]);

  const loadPolicyAndOutcomes = useCallback(async () => {
    if (!institutionId || !programmeId || !numberText(semester) || Number(semester) < 1 || Number(semester) > 12) {
      setPolicies([]);
      setOutcomes([]);
      return;
    }
    setCatalogueLoading(true);
    setError("");
    try {
      const [policyResponse, outcomeResponse] = await Promise.all([
        apiRequest<ItemList<Policy>>(`/internship-assessments/policies?institution_id=${encodeURIComponent(institutionId)}&programme_id=${encodeURIComponent(programmeId)}`),
        apiRequest<ItemList<Outcome>>(`/internship-assessments/curriculum-outcomes?institution_id=${encodeURIComponent(institutionId)}&programme_id=${encodeURIComponent(programmeId)}&semester=${Number(semester)}`),
      ]);
      setPolicies(policyResponse.items ?? []);
      setOutcomes(outcomeResponse.items ?? []);
    } catch (cause) {
      setError(readableError(cause));
    } finally {
      setCatalogueLoading(false);
    }
  }, [institutionId, programmeId, semester]);
  useEffect(() => { void loadPolicyAndOutcomes(); }, [loadPolicyAndOutcomes]);

  const updateCriterion = (index: number, field: keyof Criterion, value: string | boolean) => {
    setCriteria((current) => current.map((item, i) => i === index ? { ...item, [field]: value } : item));
  };
  const updateBand = (index: number, field: keyof GradeBand, value: string) => {
    setGradeBands((current) => current.map((item, i) => i === index ? { ...item, [field]: value } : item));
  };

  const createPolicy = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setNotice("");
    if (!institutionId || !programmeId) {
      setError("Select an institution and programme before creating a policy.");
      return;
    }
    if (criteria.length === 0 || gradeBands.length === 0) {
      setError("Add at least one rubric criterion and a complete set of grade bands.");
      return;
    }
    if (![weights.griffin, weights.curriculum, weights.faculty, griffinScoreMax, passingScore, requiredEvaluators].every(numberText) ||
        !numberText(curriculumScores.MAPPED) || !numberText(curriculumScores.PARTIALLY_MAPPED) || !numberText(curriculumScores.NOT_EVIDENCED)) {
      setError("Complete every score scale, component weight, passing score, and evaluator count.");
      return;
    }
    if (criteria.some((item) => !item.key.trim() || !item.label.trim() || !item.description.trim() || !numberText(item.max_score) || Number(item.max_score) <= 0) ||
        gradeBands.some((item) => !item.grade.trim() || !numberText(item.min_score) || !numberText(item.max_score))) {
      setError("Complete every rubric criterion and grade-band field.");
      return;
    }
    setSavingPolicy(true);
    try {
      const policy = await apiRequest<Policy>("/internship-assessments/policies", {
        method: "POST",
        body: JSON.stringify({
          institution_id: institutionId,
          programme_id: programmeId,
          name: policyName.trim(),
          criteria: criteria.map((item) => ({ ...item, key: item.key.trim(), label: item.label.trim(), description: item.description.trim(), max_score: Number(item.max_score) })),
          component_weights: { griffin: Number(weights.griffin), curriculum: Number(weights.curriculum), faculty: Number(weights.faculty) },
          griffin_score_max: Number(griffinScoreMax),
          curriculum_status_scores: {
            MAPPED: Number(curriculumScores.MAPPED),
            PARTIALLY_MAPPED: Number(curriculumScores.PARTIALLY_MAPPED),
            NOT_EVIDENCED: Number(curriculumScores.NOT_EVIDENCED),
          },
          grade_bands: gradeBands.map((item) => ({ grade: item.grade.trim(), min_score: Number(item.min_score), max_score: Number(item.max_score) })),
          passing_score: Number(passingScore),
          final_approver_role: finalApproverRole,
          required_evaluator_count: Number(requiredEvaluators),
          show_curriculum_mapping_to_evaluator: showMappingToEvaluator,
        }),
      });
      setNotice(`Policy v${policy.version} created. Earlier versions stay attached to existing evaluations; new assignments use the active policy.`);
      setPolicyName("");
      setCriteria([]);
      setWeights({ griffin: "", curriculum: "", faculty: "" });
      setGriffinScoreMax("");
      setCurriculumScores({ MAPPED: "", PARTIALLY_MAPPED: "", NOT_EVIDENCED: "" });
      setGradeBands([]);
      setPassingScore("");
      setFinalApproverRole("");
      setRequiredEvaluators("");
      setShowMappingToEvaluator(false);
      await loadPolicyAndOutcomes();
    } catch (cause) {
      setError(readableError(cause));
    } finally {
      setSavingPolicy(false);
    }
  };

  const createOutcome = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setNotice("");
    if (!institutionId || !programmeId) {
      setError("Select an institution and programme first.");
      return;
    }
    setSavingOutcome(true);
    try {
      await apiRequest<Outcome>("/internship-assessments/curriculum-outcomes", {
        method: "POST",
        body: JSON.stringify({
          institution_id: institutionId, programme_id: programmeId, semester: Number(semester),
          outcome_code: outcomeCode.trim(), title: outcomeTitle.trim(),
          expected_competency: outcomeCompetency.trim(), source_reference: outcomeSource.trim(),
        }),
      });
      setNotice("The authoritative curriculum outcome was saved. The source reference is retained for auditability.");
      setOutcomeCode(""); setOutcomeTitle(""); setOutcomeCompetency(""); setOutcomeSource("");
      await loadPolicyAndOutcomes();
    } catch (cause) {
      setError(readableError(cause));
    } finally {
      setSavingOutcome(false);
    }
  };

  if (!isInstitutionAdmin) {
    return <main className="mx-auto max-w-4xl p-6"><Card><CardHeader><CardTitle>Institution administrator access required</CardTitle><CardDescription>Assessment policies and curriculum catalogues are managed only by an authorized institution administrator.</CardDescription></CardHeader></Card></main>;
  }

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 pb-10">
      <header className="flex flex-col justify-between gap-4 border-b border-border/80 pb-6 md:flex-row md:items-end">
        <div><p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-teal-700"><ShieldCheck className="size-4" /> Academic configuration</p><h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Internship assessment policy</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">Configure a versioned rubric, component weights, score scales, grade bands, and the authorized final approver. Nothing here supplies a guessed institutional grade or a synthetic curriculum outcome.</p></div>
        <Button variant="outline" onClick={() => { void loadInstitutions(); void loadPolicyAndOutcomes(); }} disabled={loading || catalogueLoading}><RefreshCw className="mr-2 size-4" />Refresh configuration</Button>
      </header>

      {error && <Alert variant="destructive"><AlertCircle className="size-4" /><AlertTitle>Configuration needs attention</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
      {notice && <Alert className="border-teal-700/25 bg-teal-700/5 text-foreground"><ShieldCheck className="size-4 text-teal-700" /><AlertTitle>Configuration saved</AlertTitle><AlertDescription>{notice}</AlertDescription></Alert>}

      <Card className="rounded-xl border-border/80 shadow-none">
        <CardHeader><CardTitle className="text-base">Academic scope</CardTitle><CardDescription>Policies and outcomes are isolated to the selected institution and programme.</CardDescription></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2"><Label htmlFor="policy-institution">Institution</Label><Select value={institutionId} onValueChange={(value) => setInstitutionId(value ?? "")}><SelectTrigger id="policy-institution" className="w-full"><SelectValue placeholder="Choose institution" /></SelectTrigger><SelectContent>{institutions.map((item) => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}</SelectContent></Select></div>
          <div className="space-y-2"><Label htmlFor="policy-programme">Programme</Label><Select value={programmeId} onValueChange={(value) => setProgrammeId(value ?? "")}><SelectTrigger id="policy-programme" className="w-full"><SelectValue placeholder="Choose programme" /></SelectTrigger><SelectContent>{programmes.map((item) => <SelectItem key={item.id} value={item.id}>{item.name}{item.code ? ` · ${item.code}` : ""}</SelectItem>)}</SelectContent></Select></div>
          <div className="space-y-2"><Label htmlFor="curriculum-semester">Curriculum semester</Label><Input id="curriculum-semester" type="number" min={1} max={12} value={semester} onChange={(event) => setSemester(event.target.value)} required /></div>
        </CardContent>
      </Card>

      <section className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <Card className="rounded-xl border-border/80 shadow-none">
          <CardHeader><CardTitle className="text-base">Versioned grading policy</CardTitle><CardDescription>Creating a new policy increments the version and deactivates the prior version for new assignments. Existing assignments retain their rubric snapshot.</CardDescription></CardHeader>
          <CardContent>
            {catalogueLoading && policies.length === 0 ? <div className="space-y-3"><Skeleton className="h-8 w-2/3" /><Skeleton className="h-24 w-full" /></div> : policies.length === 0 ? <p className="rounded-lg border border-dashed border-border p-3 text-sm text-muted-foreground">No policy exists for this programme yet. Create a policy below before assigning evaluators.</p> : <div className="mb-6 space-y-3">{policies.map((policy) => <div key={policy.id} className="rounded-lg border border-border p-3"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-medium">{policy.name} · v{policy.version}</p><p className="mt-1 text-xs text-muted-foreground">{policy.criteria.length} rubric criteria · {policy.required_evaluator_count} independent evaluator(s) · approver: {policy.final_approver_role.replace(/_/g, " ").toLowerCase()}</p></div><Badge variant={policy.is_active ? "default" : "secondary"}>{policy.is_active ? "Active" : "Historical"}</Badge></div><div className="mt-3 grid grid-cols-3 gap-2 text-xs"><p className="rounded bg-muted/40 p-2">Griffin <strong>{policy.component_weights.griffin}%</strong></p><p className="rounded bg-muted/40 p-2">Curriculum <strong>{policy.component_weights.curriculum}%</strong></p><p className="rounded bg-muted/40 p-2">Faculty <strong>{policy.component_weights.faculty}%</strong></p></div><p className="mt-2 text-xs text-muted-foreground">Griffin max: {policy.griffin_score_max} · passing score: {policy.passing_score}/100 · curriculum status scale: {policy.curriculum_status_scores.MAPPED}/{policy.curriculum_status_scores.PARTIALLY_MAPPED}/{policy.curriculum_status_scores.NOT_EVIDENCED}</p></div>)}</div>}
            <Separator className="my-5" />
            <form onSubmit={createPolicy} className="space-y-5">
              <div className="space-y-2"><Label htmlFor="policy-name">Policy version name</Label><Input id="policy-name" value={policyName} onChange={(event) => setPolicyName(event.target.value)} placeholder="e.g. Internship assessment 2026–27" minLength={2} maxLength={255} required /></div>

              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2"><div><h3 className="font-medium">Faculty scoring rubric</h3><p className="mt-1 text-xs text-muted-foreground">Specify criterion labels, descriptions, and maximum raw scores. Comments can be mandatory.</p></div><Button type="button" size="sm" variant="outline" onClick={() => setCriteria((items) => [...items, { key: `criterion_${items.length + 1}`, label: "", description: "", max_score: "", require_comment: false }])} disabled={criteria.length >= 30}><Plus className="mr-2 size-3.5" />Add criterion</Button></div>
                {criteria.length === 0 ? <p className="rounded-lg border border-dashed border-border p-3 text-sm text-muted-foreground">No rubric criteria added. An institution-defined rubric is required.</p> : criteria.map((item, index) => <div key={index} className="space-y-3 rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between gap-2"><p className="text-sm font-medium">Criterion {index + 1}</p><Button type="button" variant="ghost" size="icon" aria-label={`Remove criterion ${index + 1}`} onClick={() => setCriteria((items) => items.filter((_, i) => i !== index))}><Trash2 className="size-4" /></Button></div>
                  <div className="grid gap-3 sm:grid-cols-2"><div className="space-y-1.5"><Label htmlFor={`criterion-key-${index}`}>Stable key</Label><Input id={`criterion-key-${index}`} value={item.key} onChange={(event) => updateCriterion(index, "key", event.target.value)} placeholder="technical_quality" required /></div><div className="space-y-1.5"><Label htmlFor={`criterion-label-${index}`}>Criterion label</Label><Input id={`criterion-label-${index}`} value={item.label} onChange={(event) => updateCriterion(index, "label", event.target.value)} required /></div></div>
                  <div className="space-y-1.5"><Label htmlFor={`criterion-description-${index}`}>Scoring guidance</Label><Textarea id={`criterion-description-${index}`} value={item.description} onChange={(event) => updateCriterion(index, "description", event.target.value)} rows={2} required /></div>
                  <div className="grid items-end gap-3 sm:grid-cols-[140px_1fr]"><div className="space-y-1.5"><Label htmlFor={`criterion-max-${index}`}>Maximum score</Label><Input id={`criterion-max-${index}`} type="number" min="0.01" step="0.01" value={item.max_score} onChange={(event) => updateCriterion(index, "max_score", event.target.value)} required /></div><div className="flex items-center gap-2 pb-2"><Checkbox id={`criterion-comment-${index}`} checked={item.require_comment} onCheckedChange={(checked) => updateCriterion(index, "require_comment", checked === true)} /><Label htmlFor={`criterion-comment-${index}`}>Require a comment when submitted</Label></div></div>
                </div>)}
              </div>

              <div className="space-y-3"><h3 className="font-medium">Component contribution weights</h3><p className="text-xs text-muted-foreground">Weights must be explicitly chosen and total exactly 100%.</p><div className="grid gap-3 sm:grid-cols-3">{(["griffin", "curriculum", "faculty"] as const).map((key) => <div key={key} className="space-y-1.5"><Label htmlFor={`weight-${key}`}>{key[0].toUpperCase() + key.slice(1)} weight (%)</Label><Input id={`weight-${key}`} type="number" min="0.01" max="100" step="0.01" value={weights[key]} onChange={(event) => setWeights((current) => ({ ...current, [key]: event.target.value }))} required /></div>)}</div></div>

              <div className="space-y-3"><h3 className="font-medium">Score normalization</h3><div className="space-y-1.5"><Label htmlFor="griffin-max">Maximum valid raw Griffin alignment score</Label><Input id="griffin-max" type="number" min="0.001" step="0.001" value={griffinScoreMax} onChange={(event) => setGriffinScoreMax(event.target.value)} placeholder="Enter the verified scale maximum" required /><p className="text-xs text-muted-foreground">Match this value to Griffin's verified score contract. The UI does not assume that a stored score is already a percentage.</p></div><div className="grid gap-3 sm:grid-cols-3">{(["MAPPED", "PARTIALLY_MAPPED", "NOT_EVIDENCED"] as const).map((status) => <div key={status} className="space-y-1.5"><Label htmlFor={`map-score-${status}`}>{status.replace(/_/g, " ").toLowerCase()} (%)</Label><Input id={`map-score-${status}`} type="number" min="0" max="100" step="0.01" value={curriculumScores[status]} onChange={(event) => setCurriculumScores((current) => ({ ...current, [status]: event.target.value }))} required /></div>)}</div><p className="text-xs text-muted-foreground">Mapped credit must be at least partially mapped credit, and partially mapped credit must be at least not-evidenced credit. Mapping must still be reviewed against actual outcomes.</p></div>

              <div className="space-y-3"><div className="flex flex-wrap items-center justify-between gap-2"><div><h3 className="font-medium">Grade bands</h3><p className="mt-1 text-xs text-muted-foreground">Bands must cover 0–100 without overlaps or gaps.</p></div><Button type="button" size="sm" variant="outline" onClick={() => setGradeBands((items) => [...items, { grade: "", min_score: "", max_score: "" }])} disabled={gradeBands.length >= 20}><Plus className="mr-2 size-3.5" />Add grade band</Button></div>
                {gradeBands.map((item, index) => <div className="grid items-end gap-3 rounded-lg border border-border p-3 sm:grid-cols-[1fr_1fr_1fr_auto]" key={index}><div className="space-y-1.5"><Label htmlFor={`grade-${index}`}>Grade label</Label><Input id={`grade-${index}`} value={item.grade} onChange={(event) => updateBand(index, "grade", event.target.value)} required /></div><div className="space-y-1.5"><Label htmlFor={`grade-min-${index}`}>Minimum (%)</Label><Input id={`grade-min-${index}`} type="number" min="0" max="100" step="0.01" value={item.min_score} onChange={(event) => updateBand(index, "min_score", event.target.value)} required /></div><div className="space-y-1.5"><Label htmlFor={`grade-max-${index}`}>Maximum (%)</Label><Input id={`grade-max-${index}`} type="number" min="0" max="100" step="0.01" value={item.max_score} onChange={(event) => updateBand(index, "max_score", event.target.value)} required /></div><Button type="button" variant="ghost" size="icon" aria-label={`Remove grade band ${index + 1}`} onClick={() => setGradeBands((items) => items.filter((_, i) => i !== index))}><Trash2 className="size-4" /></Button></div>)}
              </div>

              <div className="grid gap-3 sm:grid-cols-2"><div className="space-y-1.5"><Label htmlFor="passing-score">Minimum passing score (0–100)</Label><Input id="passing-score" type="number" min="0" max="100" step="0.01" value={passingScore} onChange={(event) => setPassingScore(event.target.value)} required /></div><div className="space-y-1.5"><Label htmlFor="required-evaluators">Required independent evaluators</Label><Select value={requiredEvaluators} onValueChange={(value) => setRequiredEvaluators(value ?? "")}><SelectTrigger id="required-evaluators" className="w-full"><SelectValue placeholder="Choose evaluator count" /></SelectTrigger><SelectContent>{[1, 2, 3, 4, 5].map((value) => <SelectItem value={String(value)} key={value}>{value} evaluator{value === 1 ? "" : "s"}</SelectItem>)}</SelectContent></Select></div></div>
              <div className="space-y-2"><Label htmlFor="final-approver">Authorized final approver role</Label><Select value={finalApproverRole} onValueChange={(value) => setFinalApproverRole(value ?? "")}><SelectTrigger id="final-approver" className="w-full"><SelectValue placeholder="Choose the official result approver" /></SelectTrigger><SelectContent><SelectItem value="INSTITUTION_ADMIN">Institution administrator</SelectItem><SelectItem value="DEAN">Dean</SelectItem><SelectItem value="DEPT_HEAD">Department head</SelectItem></SelectContent></Select><p className="text-xs text-muted-foreground">The API checks the chosen role in the current institution scope. Student and ordinary faculty roles cannot publish official results by default.</p></div>
              <div className="flex items-start gap-2 rounded-lg border border-border p-3"><Checkbox id="show-mapping-to-evaluator" checked={showMappingToEvaluator} onCheckedChange={(checked) => setShowMappingToEvaluator(checked === true)} /><div><Label htmlFor="show-mapping-to-evaluator">Allow reviewed curriculum mapping in the blind packet</Label><p className="mt-1 text-xs text-muted-foreground">Unchecked by default. Only reviewed outcome/evidence fields are exposed to the assigned evaluator; student identity and prior scores remain hidden.</p></div></div>
              <Button type="submit" disabled={savingPolicy || catalogueLoading || !institutionId || !programmeId || !finalApproverRole}><Save className="mr-2 size-4" />{savingPolicy ? "Creating policy…" : "Create new policy version"}</Button>
            </form>
          </CardContent>
        </Card>

        <Card className="rounded-xl border-border/80 shadow-none">
          <CardHeader><CardTitle className="text-base">Approved curriculum outcomes</CardTitle><CardDescription>Load the real programme outcomes using their institutional references. Kairos does not generate sample outcomes.</CardDescription></CardHeader>
          <CardContent className="space-y-5">
            <form onSubmit={createOutcome} className="space-y-4">
              <div className="space-y-1.5"><Label htmlFor="outcome-code">Outcome code</Label><Input id="outcome-code" value={outcomeCode} onChange={(event) => setOutcomeCode(event.target.value)} placeholder="Official CO/LO code" required maxLength={80} /></div>
              <div className="space-y-1.5"><Label htmlFor="outcome-title">Outcome title</Label><Input id="outcome-title" value={outcomeTitle} onChange={(event) => setOutcomeTitle(event.target.value)} required maxLength={255} /></div>
              <div className="space-y-1.5"><Label htmlFor="outcome-competency">Expected competency / learning outcome</Label><Textarea id="outcome-competency" value={outcomeCompetency} onChange={(event) => setOutcomeCompetency(event.target.value)} rows={3} required maxLength={5000} /></div>
              <div className="space-y-1.5"><Label htmlFor="outcome-source">Authoritative source reference</Label><Input id="outcome-source" value={outcomeSource} onChange={(event) => setOutcomeSource(event.target.value)} placeholder="Curriculum document title, version, page or URL" required maxLength={500} /><p className="text-xs text-muted-foreground">Provide the genuine university curriculum document/source so future reviewers can trace the outcome.</p></div>
              <Button type="submit" variant="outline" disabled={savingOutcome || !institutionId || !programmeId || !numberText(semester) || Number(semester) < 1 || Number(semester) > 12}><Plus className="mr-2 size-4" />{savingOutcome ? "Saving outcome…" : "Add curriculum outcome"}</Button>
            </form>
            <Separator />
            <div><h3 className="font-medium">Outcomes in this catalogue</h3><p className="mt-1 text-xs text-muted-foreground">Semester {semester} · {outcomes.length} stored outcome(s)</p></div>
            {catalogueLoading && outcomes.length === 0 ? <div className="space-y-3"><Skeleton className="h-14 w-full" /><Skeleton className="h-14 w-full" /></div> : outcomes.length === 0 ? <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">No outcomes stored for this programme/semester. Result calculation will remain blocked until the official curriculum is entered.</p> : <div className="space-y-2">{outcomes.map((item) => <div className="rounded-lg border border-border p-3" key={item.id}><div className="flex flex-wrap items-start justify-between gap-2"><p className="font-medium">{item.outcome_code} · {item.title}</p><Badge variant={item.is_active ? "default" : "secondary"}>{item.is_active ? "Active" : "Inactive"}</Badge></div><p className="mt-1 text-sm text-muted-foreground">{item.expected_competency}</p><p className="mt-2 text-xs text-muted-foreground">Source: {item.source_reference}</p></div>)}</div>}
          </CardContent>
        </Card>
      </section>
      <p className="text-xs leading-5 text-muted-foreground">All values are versioned and institution scoped. Changing the active policy does not rewrite previously assigned rubrics or published results. A missing Griffin contract or unreviewed curriculum remains a hard blocker to finalization.</p>
    </main>
  );
}
