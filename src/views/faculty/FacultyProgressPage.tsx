import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { AlertCircle, ArrowDownUp, RefreshCw, Search, Users } from "lucide-react";
import { apiRequest, ApiError } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Placement = { id: string; application_id: string; student_id: number | string; faculty_supervisor_id: number | string | null; start_date: string; end_date: string; status: string };
type Report = { id: string; placement_id: string; title: string; status: string; review_feedback?: string | null; updated_at?: string | null };
type StudentRow = { student_id: string; placement: Placement; reports: Report[] };
const PAGE_SIZE = 10;

export default function FacultyProgressPage() {
  const { account } = useAuth();
  const [params, setParams] = useSearchParams();
  const [placements, setPlacements] = useState<Placement[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [status, setStatus] = useState(params.get("status") ?? "ALL");
  const [sort, setSort] = useState<"student" | "start_date" | "status">("student");
  const [page, setPage] = useState(Math.max(1, Number(params.get("page") ?? 1) || 1));
  const [actionError, setActionError] = useState("");
  const [workingReport, setWorkingReport] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const results = await Promise.all([
        apiRequest<{ items: Placement[] }>("/faculty/me/placements"),
        apiRequest<{ items: Report[] }>("/reports/faculty/me"),
      ]);
      setPlacements(results[0].items ?? []);
      setReports(results[1].items ?? []);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Student progress could not be loaded.");
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const next = new URLSearchParams();
    if (search.trim()) next.set("q", search.trim());
    if (status !== "ALL") next.set("status", status);
    if (page > 1) next.set("page", String(page));
    setParams(next, { replace: true });
  }, [search, status, page, setParams]);

  const rows = useMemo<StudentRow[]>(() => {
    const byPlacement = new Map<string, Report[]>();
    reports.forEach((report) => {
      const list = byPlacement.get(report.placement_id) ?? [];
      list.push(report); byPlacement.set(report.placement_id, list);
    });
    const unique = new Map<string, StudentRow>();
    placements.forEach((placement) => {
      const key = String(placement.student_id);
      const current = unique.get(key);
      if (!current || new Date(placement.start_date).getTime() > new Date(current.placement.start_date).getTime()) {
        unique.set(key, { student_id: key, placement, reports: byPlacement.get(placement.id) ?? [] });
      }
    });
    const query = search.trim().toLowerCase();
    return [...unique.values()].filter((row) => {
      const matchesQuery = !query || row.student_id.toLowerCase().includes(query) ||
        row.reports.some((report) => report.title.toLowerCase().includes(query));
      return matchesQuery && (status === "ALL" || row.placement.status.toUpperCase() === status);
    }).sort((a, b) => sort === "start_date" ? b.placement.start_date.localeCompare(a.placement.start_date) :
      sort === "status" ? a.placement.status.localeCompare(b.placement.status) :
      a.student_id.localeCompare(b.student_id, undefined, { numeric: true }));
  }, [placements, reports, search, status, sort]);

  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const visibleRows = rows.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  const review = async (report: Report, decision: "APPROVED" | "REVISION_REQUIRED") => {
    const feedback = window.prompt(decision === "APPROVED" ? "Optional review feedback" : "Explain the changes required");
    if (decision === "REVISION_REQUIRED" && !feedback?.trim()) return;
    setWorkingReport(report.id); setActionError("");
    try {
      await apiRequest<Report>("/reports/" + encodeURIComponent(report.id) + "/status", {
        method: "PATCH", body: JSON.stringify({ status: decision, feedback_comments: feedback?.trim() || null }),
      });
      await load();
    } catch (cause) {
      setActionError(cause instanceof ApiError ? cause.message : cause instanceof Error ? cause.message : "Report review failed.");
    } finally { setWorkingReport(""); }
  };

  if (!account?.roles.some((role) => role.toUpperCase() === "FACULTY")) {
    return <main className="mx-auto max-w-5xl p-6"><Card><CardHeader><CardTitle>Faculty access required</CardTitle><CardDescription>This workspace is available to authenticated faculty accounts.</CardDescription></CardHeader><CardContent><Button asChild variant="outline"><Link to="/">Return to overview</Link></Button></CardContent></Card></main>;
  }

  return <main className="mx-auto w-full max-w-7xl space-y-6 pb-8">
    <header className="flex flex-col justify-between gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end">
      <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Faculty workspace</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Student progress</h1><p className="mt-2 max-w-2xl text-sm text-muted-foreground">Students appear only when they have a placement assigned to your faculty account. Identifiers use the existing placement relationship.</p></div>
      <Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw className="mr-2 h-4 w-4" />Refresh records</Button>
    </header>
    <div className="grid gap-3 sm:grid-cols-3">
      <Card className="shadow-none"><CardContent className="flex items-center gap-3 p-4"><Users className="h-5 w-5 text-primary"/><div><p className="text-sm text-muted-foreground">Students supervised</p><p className="text-2xl font-semibold">{loading ? "—" : rows.length}</p></div></CardContent></Card>
      <Card className="shadow-none"><CardContent className="flex items-center gap-3 p-4"><AlertCircle className="h-5 w-5 text-primary"/><div><p className="text-sm text-muted-foreground">Reports awaiting review</p><p className="text-2xl font-semibold">{loading ? "—" : reports.filter((r) => ["SUBMITTED", "UNDER_EVALUATION"].includes(r.status.toUpperCase())).length}</p></div></CardContent></Card>
      <Card className="shadow-none"><CardContent className="flex items-center gap-3 p-4"><ArrowDownUp className="h-5 w-5 text-primary"/><div><p className="text-sm text-muted-foreground">Placement records</p><p className="text-2xl font-semibold">{loading ? "—" : placements.length}</p></div></CardContent></Card>
    </div>
    {error && <div role="alert" className="flex items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm"><AlertCircle className="mt-0.5 h-4 w-4 text-destructive"/><div className="flex-1"><p className="font-medium text-destructive">Progress data unavailable</p><p className="mt-1 text-muted-foreground">{error}</p></div><Button size="sm" variant="outline" onClick={() => void load()}>Retry</Button></div>}
    {actionError && <p role="alert" className="rounded-lg border border-destructive/30 p-3 text-sm text-destructive">{actionError}</p>}
    <Card className="shadow-none"><CardHeader><CardTitle>Supervised students</CardTitle><CardDescription>Search by student identifier or report title. Statuses come from the authenticated API.</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row">
          <label className="relative flex-1"><span className="sr-only">Search students or reports</span><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"/><Input className="pl-9" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Search student ID or report title"/></label>
          <label className="sr-only" htmlFor="placement-status">Placement status</label><select id="placement-status" className="h-10 rounded-md border border-input bg-background px-3 text-sm" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="ALL">All placement statuses</option><option value="ONGOING">Ongoing</option><option value="COMPLETED">Completed</option><option value="TERMINATED">Terminated</option></select>
          <Button variant="outline" onClick={() => setSort((value) => value === "student" ? "start_date" : value === "start_date" ? "status" : "student")}><ArrowDownUp className="mr-2 h-4 w-4"/>Sort: {sort === "student" ? "Student ID" : sort === "start_date" ? "Start date" : "Status"}</Button>
          <Button variant="ghost" onClick={() => { setSearch(""); setStatus("ALL"); setSort("student"); setPage(1); }}>Reset</Button>
        </div>
        <div className="overflow-hidden rounded-lg border"><Table><TableHeader><TableRow><TableHead>Student ID</TableHead><TableHead>Placement</TableHead><TableHead>Period</TableHead><TableHead>Reports</TableHead><TableHead>Latest status</TableHead><TableHead className="text-right">Review actions</TableHead></TableRow></TableHeader>
          <TableBody>
            {loading && Array.from({ length: 4 }, (_, i) => <TableRow key={i}><TableCell colSpan={6}><Skeleton className="h-6 w-full"/></TableCell></TableRow>)}
            {!loading && !error && visibleRows.map((row) => {
              const pending = row.reports.filter((r) => ["SUBMITTED", "UNDER_EVALUATION"].includes(r.status.toUpperCase()));
              const latest = [...row.reports].sort((a,b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""))[0];
              return <TableRow key={row.student_id}><TableCell className="font-medium tabular-nums">{row.student_id}</TableCell><TableCell><Badge variant={row.placement.status.toUpperCase() === "ONGOING" ? "default" : "secondary"}>{row.placement.status.replace(/_/g," ")}</Badge></TableCell><TableCell className="text-sm text-muted-foreground">{row.placement.start_date} – {row.placement.end_date}</TableCell><TableCell>{row.reports.length}</TableCell><TableCell>{latest ? <Badge variant="outline">{latest.status.replace(/_/g," ")}</Badge> : <span className="text-sm text-muted-foreground">No report</span>}</TableCell><TableCell className="text-right">{pending.length ? <div className="flex flex-wrap justify-end gap-2">{pending.map((report) => <span key={report.id} className="inline-flex gap-1"><Button size="sm" variant="outline" disabled={workingReport === report.id} onClick={() => void review(report, "APPROVED")}>Approve</Button><Button size="sm" variant="outline" disabled={workingReport === report.id} onClick={() => void review(report, "REVISION_REQUIRED")}>Request changes</Button></span>)}</div> : <span className="text-sm text-muted-foreground">No pending action</span>}</TableCell></TableRow>;
            })}
            {!loading && !error && rows.length === 0 && <TableRow><TableCell colSpan={6} className="h-32 text-center"><p className="font-medium">No supervised students found</p><p className="mt-1 text-sm text-muted-foreground">{search || status !== "ALL" ? "Try adjusting the filters." : "Students appear here when a placement is assigned to you."}</p></TableCell></TableRow>}
          </TableBody></Table></div>
        <div className="flex flex-col justify-between gap-3 text-sm text-muted-foreground sm:flex-row sm:items-center"><span>Showing {rows.length ? (safePage - 1) * PAGE_SIZE + 1 : 0}–{Math.min(safePage * PAGE_SIZE, rows.length)} of {rows.length} students</span><div className="flex items-center gap-2"><Button variant="outline" size="sm" disabled={safePage <= 1} onClick={() => setPage((v) => Math.max(1,v-1))}>Previous</Button><span>Page {safePage} of {pageCount}</span><Button variant="outline" size="sm" disabled={safePage >= pageCount} onClick={() => setPage((v) => Math.min(pageCount,v+1))}>Next</Button></div></div>
      </CardContent>
    </Card>
  </main>;
}
