import { useId, useMemo } from "react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Skeleton } from "@/components/ui/skeleton";

export type SemesterPerformancePoint = {
  semesterId: string;
  semesterLabel: string;
  value: number | null;
  studentCount?: number;
  academicContext?: string | null;\n  metricScale?: string | null;
};

export type SemesterPerformanceChartProps = {
  title?: string;
  description?: string;
  data: SemesterPerformancePoint[];
  metricLabel: string;
  loading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  partialDataMessage?: string | null;
  onRetry?: () => void;
};

const chartConfig = {
  value: { label: "Performance", color: "var(--chart-1)" },
} satisfies ChartConfig;

export function SemesterPerformanceChart({
  title = "Semester-wise Academic Performance",
  description = "Track your academic performance across semesters.",
  data,
  metricLabel,
  loading = false,
  error = null,
  emptyMessage = "Semester-wise performance data is not available yet.",
  partialDataMessage = null,
  onRetry,
}: SemesterPerformanceChartProps) {
  const generatedId = useId().replace(/:/g, "");
  const gradientId = `semesterPerformanceFill-${generatedId}`;
  const validPoints = useMemo(
    () => data.filter((point) => point.value !== null && Number.isFinite(point.value)),
    [data],
  );
  const hasPartialData = data.some((point) => point.value === null);
  const latest = validPoints.length ? validPoints[validPoints.length - 1] : null;
  const previous = validPoints.length > 1 ? validPoints[validPoints.length - 2] : null;
  const delta = latest && previous ? latest.value! - previous.value! : null;
  const sameMetricScale = Boolean(latest?.metricScale && previous?.metricScale && latest.metricScale === previous.metricScale);

  return (
    <Card className="rounded-xl border-border/80 shadow-none">
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        {loading ? (
          <div aria-label="Loading semester performance" className="space-y-3">
            <Skeleton className="h-56 w-full" />
            <Skeleton className="h-4 w-2/5" />
          </div>
        ) : error ? (
          <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm">
            <p className="font-medium text-destructive">Performance data could not be loaded</p>
            <p className="mt-1 text-muted-foreground">{error}</p>
            {onRetry && <button type="button" onClick={onRetry} className="mt-3 rounded-md border px-3 py-1.5 font-medium hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Retry</button>}
          </div>
        ) : validPoints.length === 0 ? (
          <div className="flex min-h-56 flex-col items-center justify-center rounded-lg border border-dashed px-6 py-8 text-center">
            <p className="font-medium">No semester results available</p>
            <p className="mt-1 max-w-lg text-sm leading-6 text-muted-foreground">{emptyMessage}</p>
          </div>
        ) : (
          <>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="text-muted-foreground">{metricLabel}</span>
              {latest && <span className="font-semibold tabular-nums">Latest: {latest.value!.toLocaleString(undefined, { maximumFractionDigits: 3 })}</span>}
            </div>
            <ChartContainer config={chartConfig} className="h-[260px] w-full aspect-auto">
              <AreaChart accessibilityLayer data={data} margin={{ left: 4, right: 12, top: 12, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="semesterLabel" tickLine={false} axisLine={false} tickMargin={8} minTickGap={12} />
                <YAxis tickLine={false} axisLine={false} width={42} />
                <ChartTooltip
                  cursor={false}
                  content={<ChartTooltipContent formatter={(value) => <span className="font-mono font-medium tabular-nums">{value == null ? "No result" : `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 3 })} ${metricLabel}`}</span>} />}
                />
                <defs>
                  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-value)" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="var(--color-value)" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <Area dataKey="value" name="Performance" type="monotone" stroke="var(--color-value)" strokeWidth={2} fill={`url(#${gradientId})`} connectNulls={false} />
              </AreaChart>
            </ChartContainer>
            {hasPartialData && <p className="mt-3 text-xs text-muted-foreground">{partialDataMessage ?? "Some semesters have no recorded result; missing values are not treated as zero."}</p>}
          </>
        )}
      </CardContent>
      {!loading && !error && latest && previous && delta !== null && sameMetricScale && (
        <CardFooter className="gap-2 border-t text-sm text-muted-foreground">
          {delta > 0 ? <TrendingUp className="h-4 w-4 text-emerald-600" aria-hidden="true" /> : delta < 0 ? <TrendingDown className="h-4 w-4 text-destructive" aria-hidden="true" /> : null}
          <span>Change from previous recorded semester: <strong className="font-medium text-foreground tabular-nums">{delta > 0 ? "+" : ""}{delta.toLocaleString(undefined, { maximumFractionDigits: 3 })} {metricLabel}</strong></span>
        </CardFooter>
      )}
    </Card>
  );
}
