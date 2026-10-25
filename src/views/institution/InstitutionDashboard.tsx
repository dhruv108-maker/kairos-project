import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { Activity, AlertCircle, BookOpen, Building2, CalendarDays, GraduationCap, RefreshCw, School, Users } from "lucide-react";
import { apiRequest, ApiError } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type Institution = { id: string; name: string; slug: string; status: string; city?: string | null; state?: string | null; institution_type?: string | null };
type Item<T> = { items: T[] };
type Member = { account_id: string; role: string; status: string };
type AcademicItem = { id: string; name?: string; code?: string; is_active?: boolean; year_label?: string; is_current?: boolean; start_date?: string; end_date?: string; graduation_year?: number };
type AuditEvent = { id: string; action: string; entity_type: string; entity_id: string | null; created_at: string };

export default function InstitutionDashboard() {
  const { account } = useAuth();
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [institutionId, setInstitutionId] = useState("");
  const [members, setMembers] = useState<Member[]>([]);
  const [schools, setSchools] = useState<AcademicItem[]>([]);
  const [departments, setDepartments] = useState<AcademicItem[]>([]);
  const [programmes, setProgrammes] = useState<AcademicItem[]>([]);
  const [years, setYears] = useState<AcademicItem[]>([]);
  const [cohorts, setCohorts] = useState<AcademicItem[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const admin = account?.roles.some((role) => role.toUpperCase() === "INSTITUTION_ADMIN");
  const selected = institutions.find((item) => item.id === institutionId);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const response = await apiRequest<Item<Institution>>("/institutions");
      const available = response.items ?? [];
      setInstitutions(available);
      const id = institutionId && available.some((item) => item.id === institutionId) ? institutionId : available[0]?.id ?? "";
      setInstitutionId(id);
      if (!id) { setMembers([]); setSchools([]); setDepartments([]); setProgrammes([]); setYears([]); setCohorts([]); setEvents([]); return; }
      const base = "/institutions/" + encodeURIComponent(id);
      const result = await Promise.all([
        apiRequest<Item<Member>>(base + "/members"),
        apiRequest<Item<AcademicItem>>(base + "/schools"),
        apiRequest<Item<AcademicItem>>(base + "/departments"),
        apiRequest<Item<AcademicItem>>(base + "/programmes"),
        apiRequest<Item<AcademicItem>>(base + "/academic-years"),
        apiRequest<Item<AcademicItem>>(base + "/cohorts"),
        apiRequest<Item<AuditEvent>>(base + "/audit-events?limit=8&offset=0"),
      ]);
      setMembers(result[0].items ?? []); setSchools(result[1].items ?? []); setDepartments(result[2].items ?? []);
      setProgrammes(result[3].items ?? []); setYears(result[4].items ?? []); setCohorts(result[5].items ?? []); setEvents(result[6].items ?? []);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : cause instanceof Error ? cause.message : "Institution data could not be loaded.");
    } finally { setLoading(false); }
  }, [institutionId, refresh]);

  useEffect(() => { void load(); }, [load]);

  if (!admin) return <main className="mx-auto max-w-4xl p-6"><Card><CardHeader><CardTitle>Institution administrator access required</CardTitle><CardDescription>This workspace is available to institution administrators.</CardDescription></CardHeader><CardContent><Button asChild variant="outline"><Link to="/">Return to overview</Link></Button></CardContent></Card></main>;

  const metric = (title: string, value: number, note: string, Icon: typeof Users) => <Card className="shadow-none"><CardContent className="flex items-center gap-3 p-5"><div className="rounded-xl bg-primary/10 p-3"><Icon className="h-5 w-5 text-primary" /></div><div><p className="text-sm text-muted-foreground">{title}</p><p className="mt-1 text-2xl font-semibold">{loading ? "—" : value}</p><p className="mt-1 text-xs text-muted-foreground">{note}</p></div></CardContent></Card>;
  const currentYear = years.find((year) => year.is_current);

  return <main className="mx-auto w-full max-w-7xl space-y-6 pb-10">
    <header className="flex flex-col justify-between gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Institution workspace</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Administration dashboard</h1><p className="mt-2 text-sm text-muted-foreground">Membership, academic structure, and recent administrative activity in one place.</p></div><Button variant="outline" onClick={() => setRefresh((n) => n + 1)} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />Refresh data</Button></header>
    {error && <div role="alert" className="flex items-start gap-3 rounded-xl border border-destructive/30 p-4 text-sm"><AlertCircle className="mt-0.5 h-4 w-4 text-destructive" /><div className="flex-1"><p className="font-medium text-destructive">Dashboard data unavailable</p><p className="mt-1 text-muted-foreground">{error}</p></div><Button size="sm" variant="outline" onClick={() => setRefresh((n) => n + 1)}>Retry</Button></div>}
    <Card className="shadow-none"><CardContent className="flex flex-col justify-between gap-4 p-5 sm:flex-row sm:items-center"><div className="flex items-center gap-3"><div className="rounded-xl bg-primary/10 p-3"><Building2 className="h-5 w-5 text-primary" /></div><div><p className="font-semibold">{selected?.name ?? (loading ? "Loading institution…" : "No institution available")}</p><p className="text-sm text-muted-foreground">{selected ? [selected.city, selected.state, selected.institution_type?.replaceAll("_", " ")].filter(Boolean).join(" · ") || selected.slug : "Check your institution membership."}</p></div></div>{institutions.length > 1 && <select aria-label="Choose institution" className="h-10 rounded-md border border-input bg-background px-3" value={institutionId} onChange={(e) => setInstitutionId(e.target.value)}>{institutions.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>}{selected && <Badge variant={selected.status.toUpperCase() === "ACTIVE" ? "default" : "secondary"}>{selected.status.replaceAll("_", " ")}</Badge>}</CardContent></Card>
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{metric("Active members", members.filter((m) => m.status.toUpperCase() === "ACTIVE").length, members.length + " total memberships", Users)}{metric("Schools", schools.length, "Institution-level units", School)}{metric("Departments", departments.length, "Registered departments", BookOpen)}{metric("Programmes", programmes.length, cohorts.length + " cohorts registered", GraduationCap)}</section>
    <section className="grid gap-4 lg:grid-cols-2">
      <Card className="shadow-none"><CardHeader><CardTitle>Academic structure</CardTitle><CardDescription>Current catalogue and academic-year settings.</CardDescription></CardHeader><CardContent className="space-y-4"><div className="flex items-center gap-3 rounded-lg border p-4"><CalendarDays className="h-5 w-5 text-primary" /><div className="flex-1"><p className="text-sm font-medium">Current academic year</p><p className="text-sm text-muted-foreground">{currentYear ? `${currentYear.year_label} · ${currentYear.start_date} to ${currentYear.end_date}` : "No year marked current"}</p></div><Badge variant={currentYear ? "default" : "secondary"}>{currentYear ? "Current" : "Not set"}</Badge></div><div className="grid grid-cols-3 gap-3">{[[ "Academic years", years.length ], ["Active schools", schools.filter((s) => s.is_active).length], ["Active cohorts", cohorts.filter((c) => c.is_active).length]].map(([label, value]) => <div key={String(label)} className="rounded-lg bg-muted/50 p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-xl font-semibold">{loading ? "—" : value}</p></div>)}</div><div className="flex flex-wrap gap-2"><Button asChild size="sm" variant="outline"><Link to="/institution/academics">Manage academic structure</Link></Button><Button asChild size="sm" variant="outline"><Link to="/institution/members">Manage members</Link></Button></div></CardContent></Card>
      <Card className="shadow-none"><CardHeader><CardTitle className="flex items-center gap-2"><Activity className="h-5 w-5 text-primary" />Recent activity</CardTitle><CardDescription>Latest institution administration audit events.</CardDescription></CardHeader><CardContent className="space-y-4">{loading && [1,2,3].map((n) => <div key={n} className="space-y-2"><Skeleton className="h-4 w-2/3" /><Skeleton className="h-3 w-1/2" /></div>)}{!loading && events.map((event) => <div key={event.id} className="flex gap-3 border-b border-border/70 pb-3 last:border-0"><div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" /><div className="min-w-0"><p className="break-words text-sm font-medium">{event.action.replaceAll(".", " ").replaceAll("_", " ")}</p><p className="text-xs text-muted-foreground">{event.entity_type}{event.entity_id ? " · " + event.entity_id : ""}</p><p className="mt-1 text-xs text-muted-foreground">{new Date(event.created_at).toLocaleString()}</p></div></div>)}{!loading && !events.length && <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">No activity recorded yet.</p>}<Button asChild variant="ghost" size="sm" className="w-full"><Link to={selected ? "/institution/audit?institution=" + encodeURIComponent(selected.id) : "/"}>View audit history</Link></Button></CardContent></Card>
    </section>
  </main>;
}
