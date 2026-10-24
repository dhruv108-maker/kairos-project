import { useEffect, useMemo, useState } from "react";
import { AlertCircle, BarChart3 } from "lucide-react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { apiRequest } from "@/api/kairos-client";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type PerformancePoint = { semester: string; average: number; students?: number };
type Scope = "personal" | "student" | "mentees" | "batch" | "department" | "school";
type PerformanceResponse = { items?: PerformancePoint[]; scope_label?: string; metric_label?: string; note?: string };
type Props = { role: "student" | "faculty" | "authority" | "platform" };

const chartConfig = {
  average: { label: "Average performance", color: "var(--chart-1)" },
} satisfies ChartConfig;

const scopeOptions: Record<Exclude<Props["role"], "student">, { value: Scope; label: string }[]> = {
  faculty: [
    { value: "student", label: "Individual student" },
    { value: "mentees", label: "Mentees consolidated" },
    { value: "batch", label: "Batch / class" },
    { value: "department", label: "Department" },
    { value: "school", label: "School" },
  ],
  authority: [
    { value: "student", label: "Individual student" },
    { value: "batch", label: "Batch / class" },
    { value: "department", label: "Department" },
    { value: "school", label: "School" },
  ],
  platform: [
    { value: "student", label: "Individual student" },
    { value: "batch", label: "Batch / class" },
    { value: "department", label: "Department" },
    { value: "school", label: "School" },
  ],
};

export function SemesterPerformanceChart({ role }: Props) {
  const [scope, setScope] = useState<Scope>(role === "student" ? "personal" : role === "faculty" ? "mentees" : "school");
  const [data, setData] = useState<PerformancePoint[]>([]);
  const [scopeLabel, setScopeLabel] = useState("");
  const [metricLabel, setMetricLabel] = useState("Average performance");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setNote("");
    // This endpoint is the agreed UI contract for the semester chart. It must enforce
    // the caller's student/mentorship/cohort/department/school access on the server.
    apiRequest<PerformanceResponse>(`/analytics/semester-performance?scope=${encodeURIComponent(scope)}`)
      .then((result) => {
        if (!active) return;
        setData(Array.isArray(result.items) ? result.items.filter((item) => Number.isFinite(item.average)) : []);
        setScopeLabel(result.scope_label ?? "");
        setMetricLabel(result.metric_label ?? "Average performance");
        setNote(result.note ?? "");
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Semester performance could not be loaded.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [scope]);

  const description = role === "student"
    ? "Your own recorded performance, semester by semester."
    : "Compare recorded performance over semesters within the selected authorized scope.";
  const options = role === "student" ? [] : scopeOptions[role];
  const latest = useMemo(() => data.length ? data[data.length - 1] : null, [data]);

  return (
    <Card className="rounded-xl border-border/80 shadow-none">
      <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="rounded-lg border border-primary/15 bg-primary/5 p-2 text-primary"><BarChart3 className="h-5 w-5" aria-hidden="true" /></span>
          <div>
            <CardTitle className="text-base">Semester-wise performance</CardTitle>
            <CardDescription className="mt-1">{description}</CardDescription>
            {scopeLabel && <Badge variant="secondary" className="mt-2">{scopeLabel}</Badge>}
          </div>
        </div>
        {options.length > 0 && (
          <div className="w-full sm:w-56">
            <label htmlFor="semester-performance-scope" className="mb-1.5 block text-xs font-medium text-muted-foreground">Performance scope</label>
            <Select value={scope} onValueChange={(value) => setScope(value as Scope)}>
              <SelectTrigger id="semester-performance-scope"><SelectValue placeholder="Select scope" /></SelectTrigger>
              <SelectContent>{options.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        )}
      </CardHeader>
      <CardContent>
        {loading ? <div className="space-y-3"><Skeleton className="h-56 w-full" /><Skeleton className="h-4 w-2/5" /></div>
          : error ? <div role="status" className="flex items-start gap-2 rounded-lg border border-dashed p-4 text-sm text-muted-foreground"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><div><p className="font-medium text-foreground">Performance data unavailable</p><p className="mt-1">{error}</p></div></div>
          : data.length ? <>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm"><span className="text-muted-foreground">{metricLabel}</span>{latest && <span className="font-semibold tabular-nums">Latest: {latest.average.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>}</div>
            <ChartContainer config={chartConfig} className="h-[260px] w-full aspect-auto">
              <AreaChart accessibilityLayer data={data} margin={{ left: 4, right: 12, top: 12, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="semester" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} width={36} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <defs><linearGradient id="semesterPerformanceFill" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="var(--color-average)" stopOpacity={0.35} /><stop offset="95%" stopColor="var(--color-average)" stopOpacity={0.03} /></linearGradient></defs>
                <Area dataKey="average" type="monotone" stroke="var(--color-average)" strokeWidth={2} fill="url(#semesterPerformanceFill)" connectNulls={false} />
              </AreaChart>
            </ChartContainer>
            {note && <p className="mt-3 text-xs text-muted-foreground">{note}</p>}
          </> : <div className="flex min-h-56 flex-col items-center justify-center rounded-lg border border-dashed px-6 py-8 text-center"><BarChart3 className="h-8 w-8 text-muted-foreground/70" /><p className="mt-3 font-medium">No semester performance recorded</p><p className="mt-1 max-w-lg text-sm leading-6 text-muted-foreground">{note || "This chart only displays persisted semester-grade data returned by the authorized performance API. No sample or estimated grades are shown."}</p></div>}
      </CardContent>
    </Card>
  );
}
