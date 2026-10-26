import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, ChartNoAxesColumn, RefreshCw } from "lucide-react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { apiRequest, ApiError } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Result = { id: string; report_submission_id: string; report_version_id: string; academic_year_id: string | null; semester_number: number | null; status: string; total_score: string; final_grade: string | null; published_at: string | null; grading_policy_id: string };
const chartConfig = { score: { label: "Published score" } } satisfies ChartConfig;

export default function StudentPerformancePage() {
  const { account } = useAuth();
  const [items, setItems] = useState<Result[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const response = await apiRequest<{ items: Result[] }>("/academic-results/me");
      setItems(response.items ?? []);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : cause instanceof Error ? cause.message : "Academic results could not be loaded.");
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const chartData = useMemo(() => items.slice().reverse().map((item, index) => ({
    label: "S" + (item.semester_number ?? "—") + " · " + (item.academic_year_id ?? "Year not recorded"),
    score: Number(item.total_score),
    sequence: index + 1,
  })).filter((item) => Number.isFinite(item.score)), [items]);

  if (!account?.roles.some((role) => role.toUpperCase() === "STUDENT")) {
    return <main className="mx-auto max-w-4xl p-6"><Card><CardHeader><CardTitle>Student access required</CardTitle><CardDescription>This view shows only results belonging to the authenticated student account.</CardDescription></CardHeader></Card></main>;
  }

  return <main className="mx-auto w-full max-w-6xl space-y-6 pb-10">
    <header className="flex flex-col justify-between gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end"><div><div className="flex items-center gap-2 text-sm font-medium text-primary"><ChartNoAxesColumn className="h-4 w-4" /> Academic record</div><h1 className="mt-2 text-3xl font-semibold tracking-tight">Internship performance</h1><p className="mt-2 max-w-2xl text-sm text-muted-foreground">Only published, persisted internship results are shown. Draft and unpublished assessment scores are never exposed here.</p></div><Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button></header>
    {error && <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Results unavailable</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
    {loading ? <div className="grid gap-4 md:grid-cols-2"><Card><CardHeader><Skeleton className="h-5 w-40" /></CardHeader><CardContent><Skeleton className="h-48 w-full" /></CardContent></Card><Card><CardHeader><Skeleton className="h-5 w-40" /></CardHeader><CardContent><Skeleton className="h-48 w-full" /></CardContent></Card></div> :
      items.length === 0 ? <Card><CardContent className="flex flex-col items-center gap-3 py-16 text-center"><ChartNoAxesColumn className="h-9 w-9 text-muted-foreground" /><h2 className="text-lg font-semibold">No published internship results yet</h2><p className="max-w-lg text-sm text-muted-foreground">When your institution approves and publishes an internship result, it will appear here. Missing results are not treated as zero.</p></CardContent></Card> :
      <>
        <Card><CardHeader><CardTitle>Published score history</CardTitle><CardDescription>Scores are on the institution-approved calculation scale. Each bar is a published internship result; this is not your GPA or CGPA.</CardDescription></CardHeader><CardContent><ChartContainer config={chartConfig} className="min-h-[280px] w-full"><BarChart accessibilityLayer data={chartData}><CartesianGrid vertical={false} /><XAxis dataKey="label" tickLine={false} axisLine={false} interval={0} angle={-15} textAnchor="end" height={65} /><YAxis domain={[0, 100]} tickLine={false} axisLine={false} /><ChartTooltip content={<ChartTooltipContent />} /><Bar dataKey="score" fill="var(--color-score)" radius={4} /></BarChart></ChartContainer><p className="mt-3 text-sm text-muted-foreground">Text alternative: the table below lists each published score, semester context, and grade.</p></CardContent></Card>
        <Card><CardHeader><CardTitle>Published results</CardTitle><CardDescription>Policy and report-version references are retained for traceability.</CardDescription></CardHeader><CardContent><Table><TableHeader><TableRow><TableHead>Semester</TableHead><TableHead>Academic year</TableHead><TableHead>Score</TableHead><TableHead>Grade</TableHead><TableHead>Status</TableHead><TableHead>Published</TableHead></TableRow></TableHeader><TableBody>{items.map((item) => <TableRow key={item.id}><TableCell>{item.semester_number == null ? "Not recorded" : "Semester " + item.semester_number}</TableCell><TableCell>{item.academic_year_id ?? "Not recorded"}</TableCell><TableCell className="font-medium tabular-nums">{item.total_score}</TableCell><TableCell>{item.final_grade ?? "Not configured"}</TableCell><TableCell><Badge variant="secondary">{item.status}</Badge></TableCell><TableCell>{item.published_at ? new Date(item.published_at).toLocaleDateString() : "—"}</TableCell></TableRow>)}</TableBody></Table></CardContent></Card>
      </>}
  </main>;
}
