import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from "react";
import {
  AlertCircle, ArrowUpRight, BookOpen, BriefcaseBusiness, Check, ChevronRight,
  FileText, GraduationCap, Link2, LoaderCircle, Plus, Save, Trash2, UploadCloud,
  UserRound, Wrench, X,
} from "lucide-react";
import { apiRequest, ApiError } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";

type PortfolioKind = "skills" | "projects" | "experience" | "research" | "certifications" | "awards" | "achievements" | "activities";
type PortfolioEntry = {
  id: string; title: string; description?: string | null; organization?: string | null;
  url?: string | null; credential_id?: string | null; proficiency?: string | null;
  start_date?: string | null; end_date?: string | null; issued_date?: string | null;
  created_at?: string;
};
type AcademicEntry = {
  id: string; institution_name: string; qualification: string; field_of_study?: string | null;
  start_date?: string | null; end_date?: string | null; semester?: string | null;
  grade_value?: number | string | null; grade_max?: number | string | null;
  grading_scale?: string | null; description?: string | null; is_verified?: boolean;
};
type ResumeEntry = { id: string; storage_file_id: string; label: string; is_primary: boolean; created_at: string };
type CvData = { profile: { full_name: string; email: string; phone_number: string | null }; academics: AcademicEntry[] } & Partial<Record<PortfolioKind, PortfolioEntry[]>>;
type Completion = { percentage: number; completed: number; total: number; sections?: Record<string, boolean> };
type Section = { id: string; label: string; description: string; icon: typeof UserRound; kind?: PortfolioKind | "academics" | "personal" | "resumes" };

const sections: Section[] = [
  { id: "personal", label: "Personal information", description: "The basics recruiters and faculty use to identify you.", icon: UserRound, kind: "personal" },
  { id: "academics", label: "Education", description: "Your education history and stated academic results.", icon: GraduationCap, kind: "academics" },
  { id: "skills", label: "Skills", description: "Skills you want to highlight. Proficiency is optional.", icon: Wrench, kind: "skills" },
  { id: "experience", label: "Experience", description: "Internships, work experience, and responsibilities.", icon: BriefcaseBusiness, kind: "experience" },
  { id: "projects", label: "Projects", description: "Academic and personal projects you have worked on.", icon: BookOpen, kind: "projects" },
  { id: "research", label: "Research", description: "Research work and publications you choose to list.", icon: BookOpen, kind: "research" },
  { id: "certifications", label: "Certifications", description: "Credentials and certificates you have earned.", icon: Check, kind: "certifications" },
  { id: "achievements", label: "Achievements & activities", description: "Awards, leadership, volunteering, and other activities.", icon: Link2, kind: "achievements" },
  { id: "resumes", label: "Resume & documents", description: "Manage the resumes attached to your profile.", icon: FileText, kind: "resumes" },
];
const collections: PortfolioKind[] = ["skills", "projects", "experience", "research", "certifications", "awards", "achievements", "activities"];
const blankEntry = { title: "", description: "", organization: "", url: "", credential_id: "", proficiency: "", start_date: "", end_date: "", issued_date: "" };
const blankAcademic = { institution_name: "", qualification: "", field_of_study: "", start_date: "", end_date: "", semester: "", grade_value: "", grade_max: "", grading_scale: "", description: "" };
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}
function dateText(value?: string | null) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString(undefined, { month: "short", year: "numeric", timeZone: "UTC" });
}

export default function StudentProfileBuilder() {
  const { account } = useAuth();
  const [cv, setCv] = useState<CvData | null>(null);
  const [completion, setCompletion] = useState<Completion | null>(null);
  const [resumes, setResumes] = useState<ResumeEntry[]>([]);
  const [activeSection, setActiveSection] = useState("personal");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [entryKind, setEntryKind] = useState<PortfolioKind>("skills");
  const [entryForm, setEntryForm] = useState({ ...blankEntry });
  const [editingEntryId, setEditingEntryId] = useState<string | null>(null);
  const [academicForm, setAcademicForm] = useState({ ...blankAcademic });
  const [editingAcademicId, setEditingAcademicId] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const dirtyPersonal = useMemo(() => !!cv && (fullName !== cv.profile.full_name || phone !== (cv.profile.phone_number ?? "")), [cv, fullName, phone]);

  const refresh = useCallback(async () => {
    const [cvResult, completionResult, resumeResult] = await Promise.all([
      apiRequest<CvData>("/students/me/cv"),
      apiRequest<Completion>("/students/me/completeness").catch(() => null),
      apiRequest<{ items: ResumeEntry[] }>("/students/me/resumes"),
    ]);
    setCv(cvResult);
    setFullName(cvResult.profile.full_name ?? "");
    setPhone(cvResult.profile.phone_number ?? "");
    setCompletion(completionResult);
    setResumes(resumeResult.items ?? []);
  }, []);

  useEffect(() => {
    let alive = true;
    Promise.all([
      apiRequest<CvData>("/students/me/cv"),
      apiRequest<Completion>("/students/me/completeness").catch(() => null),
      apiRequest<{ items: ResumeEntry[] }>("/students/me/resumes"),
    ]).then(([cvResult, completionResult, resumeResult]) => {
      if (!alive) return;
      setCv(cvResult);
      setFullName(cvResult.profile.full_name ?? "");
      setPhone(cvResult.profile.phone_number ?? "");
      setCompletion(completionResult);
      setResumes(resumeResult.items ?? []);
      setError("");
    }).catch((err: unknown) => { if (alive) setError(errorMessage(err)); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  const persistPersonal = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true); setError(""); setNotice("");
    try {
      const updated = await apiRequest<CvData>("/students/me/cv", {
        method: "PATCH", body: JSON.stringify({ full_name: fullName.trim(), phone_number: phone.trim() || null }),
      });
      setCv((current) => current ? { ...current, profile: updated.profile } : updated);
      setFullName(updated.profile.full_name);
      setPhone(updated.profile.phone_number ?? "");
      setNotice("Personal information saved.");
      await refresh();
    } catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  };

  const saveEntry = async (event: FormEvent) => {
    event.preventDefault();
    if (!entryForm.title.trim()) { setError("Add a title before saving."); return; }
    setSaving(true); setError(""); setNotice("");
    const payload = Object.fromEntries(Object.entries(entryForm).map(([key, value]) => [key, value.trim() || null]));
    try {
      await apiRequest<PortfolioEntry>(editingEntryId
        ? `/students/me/${entryKind}/${encodeURIComponent(editingEntryId)}`
        : `/students/me/${entryKind}`, {
        method: editingEntryId ? "PATCH" : "POST", body: JSON.stringify(payload),
      });
      setEntryForm({ ...blankEntry }); setEditingEntryId(null);
      await refresh(); setNotice(`${sections.find((section) => section.kind === entryKind)?.label ?? "Profile entry"} saved.`);
    } catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  };

  const saveAcademic = async (event: FormEvent) => {
    event.preventDefault();
    if (!academicForm.institution_name.trim() || !academicForm.qualification.trim()) {
      setError("Institution and qualification are required."); return;
    }
    setSaving(true); setError(""); setNotice("");
    const payload = Object.fromEntries(Object.entries(academicForm).map(([key, value]) => {
      if (key === "grade_value" || key === "grade_max") return [key, value.trim() ? Number(value) : null];
      return [key, value.trim() || null];
    }));
    try {
      await apiRequest<AcademicEntry>(editingAcademicId
        ? `/students/me/academic-records/${encodeURIComponent(editingAcademicId)}`
        : "/students/me/academic-records", {
        method: editingAcademicId ? "PATCH" : "POST", body: JSON.stringify(payload),
      });
      setAcademicForm({ ...blankAcademic }); setEditingAcademicId(null);
      await refresh(); setNotice("Education record saved. Student-entered records are not institution-verified.");
    } catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  };

  const removeEntry = async (kind: PortfolioKind, id: string) => {
    if (!window.confirm("Delete this profile entry? This cannot be undone.")) return;
    setError(""); setNotice("");
    try { await apiRequest<void>(`/students/me/${kind}/${encodeURIComponent(id)}`, { method: "DELETE" }); await refresh(); setNotice("Profile entry deleted."); }
    catch (err) { setError(errorMessage(err)); }
  };
  const removeAcademic = async (id: string) => {
    if (!window.confirm("Delete this education record? This cannot be undone.")) return;
    setError(""); setNotice("");
    try { await apiRequest<void>(`/students/me/academic-records/${encodeURIComponent(id)}`, { method: "DELETE" }); await refresh(); setNotice("Education record deleted."); }
    catch (err) { setError(errorMessage(err)); }
  };
  const removeResume = async (resume: ResumeEntry) => {
    if (!window.confirm("Remove this resume from your profile?")) return;
    setError(""); setNotice("");
    try { await apiRequest<void>(`/students/me/resumes/${encodeURIComponent(resume.id)}`, { method: "DELETE" }); await refresh(); setNotice("Resume removed from your profile. The stored file is retained."); }
    catch (err) { setError(errorMessage(err)); }
  };

  const uploadFile = async (file?: File) => {
    if (!file) return;
    setError(""); setNotice("");
    if (!["application/pdf", "text/plain"].includes(file.type) || !/\.(pdf|txt)$/i.test(file.name)) {
      setError("Choose a PDF or plain-text CV. These are the formats supported for this upload flow."); return;
    }
    if (file.size > MAX_UPLOAD_BYTES) { setError("This file exceeds Kairos's 10 MiB upload limit."); return; }
    if (file.size === 0) { setError("This file is empty."); return; }
    setUploading(true);
    let storageId: string | null = null;
    try {
      const form = new FormData(); form.append("file", file);
      const stored = await apiRequest<{ id: string; original_name: string }>("/storage/upload", { method: "POST", body: form });
      storageId = stored.id;
      await apiRequest<ResumeEntry>("/students/me/resumes", {
        method: "POST", body: JSON.stringify({ storage_file_id: stored.id, label: file.name, is_primary: resumes.length === 0 }),
      });
      await refresh();
      setNotice("CV uploaded and attached to your profile. Automatic CV extraction is not currently available.");
    } catch (err) {
      if (storageId) {
        try { await apiRequest<void>(`/storage/${encodeURIComponent(storageId)}`, { method: "DELETE" }); } catch { /* Keep the original error visible if cleanup is not possible. */ }
      }
      setError(errorMessage(err));
    } finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  };
  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault(); setDragging(false);
    void uploadFile(event.dataTransfer.files?.[0]);
  };

  const openDrawer = (section = "personal") => { setActiveSection(section); setDrawerOpen(true); setError(""); setNotice(""); };
  const selected = sections.find((section) => section.id === activeSection) ?? sections[0];
  const entriesFor = (kind: PortfolioKind) => cv?.[kind] ?? [];
  const beginEditEntry = (kind: PortfolioKind, entry: PortfolioEntry) => {
    setEntryKind(kind); setEditingEntryId(entry.id);
    setEntryForm(Object.fromEntries(Object.keys(blankEntry).map((key) => [key, String(entry[key as keyof PortfolioEntry] ?? "")])) as typeof blankEntry);
  };
  const beginEditAcademic = (item: AcademicEntry) => {
    setEditingAcademicId(item.id);
    setAcademicForm(Object.fromEntries(Object.keys(blankAcademic).map((key) => [key, String(item[key as keyof AcademicEntry] ?? "")])) as typeof blankAcademic);
  };
  const startNewEntry = (kind: PortfolioKind) => { setEntryKind(kind); setEditingEntryId(null); setEntryForm({ ...blankEntry }); setError(""); };

  if (!account?.roles.some((role) => role.toUpperCase() === "STUDENT")) {
    return <div className="mx-auto max-w-4xl p-6"><Card><CardContent className="p-6 text-sm text-muted-foreground">The student profile builder is available to authenticated student accounts.</CardContent></Card></div>;
  }

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 pb-10">
      <section className="rounded-2xl border bg-gradient-to-br from-teal-50/80 via-background to-background p-6 sm:p-8 dark:from-teal-950/20">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-teal-700 dark:text-teal-300">KAIROS / STUDENT PROFILE</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Your profile, your story.</h1>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">Build a profile that reflects your education, skills, and experience. Add only what you want to share; your entries remain editable.</p>
          </div>
          <Button onClick={() => openDrawer()} className="shrink-0 gap-2"><Plus className="h-4 w-4" /> Build your student profile</Button>
        </div>
        <div className="mt-7 grid gap-3 sm:grid-cols-3">
          <Card className="border-border/70 bg-background/90 shadow-none"><CardContent className="p-4"><p className="text-xs text-muted-foreground">Profile name</p><p className="mt-1 truncate font-medium">{cv?.profile.full_name || account.full_name || "Add your name"}</p></CardContent></Card>
          <Card className="border-border/70 bg-background/90 shadow-none"><CardContent className="p-4"><p className="text-xs text-muted-foreground">Education records</p><p className="mt-1 text-2xl font-semibold tabular-nums">{cv?.academics.length ?? "—"}</p></CardContent></Card>
          <Card className="border-border/70 bg-background/90 shadow-none"><CardContent className="p-4"><p className="text-xs text-muted-foreground">Resume documents</p><p className="mt-1 text-2xl font-semibold tabular-nums">{resumes.length}</p></CardContent></Card>
        </div>
      </section>

      {error && !drawerOpen && <div role="alert" className="flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
      {loading ? <Card><CardContent className="p-8 text-sm text-muted-foreground">Loading your saved profile…</CardContent></Card> : (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
          <Card className="shadow-none"><CardHeader><CardTitle className="text-base">Profile sections</CardTitle><CardDescription>Choose a section to add or update your information.</CardDescription></CardHeader><CardContent className="divide-y">
            {sections.map((section) => {
              const Icon = section.icon;
              const count = section.kind === "academics" ? (cv?.academics.length ?? 0) : section.kind === "personal" ? (cv?.profile.full_name ? 1 : 0) : section.kind === "resumes" ? resumes.length : entriesFor(section.kind as PortfolioKind).length;
              return <button key={section.id} onClick={() => openDrawer(section.id)} className="flex w-full items-center gap-3 py-4 text-left outline-none transition-colors hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring">
                <span className="rounded-lg border bg-muted/40 p-2 text-teal-700 dark:text-teal-300"><Icon className="h-4 w-4" /></span><span className="min-w-0 flex-1"><span className="block text-sm font-medium">{section.label}</span><span className="mt-0.5 block text-xs text-muted-foreground">{section.description}</span></span><Badge variant="secondary">{count}</Badge><ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>;
            })}
          </CardContent></Card>
          <div className="space-y-4">
            <Card className="shadow-none"><CardHeader><CardTitle className="text-base">Profile completion</CardTitle><CardDescription>Calculated by Kairos from the saved profile, when available.</CardDescription></CardHeader><CardContent>{completion ? <><div className="flex items-baseline justify-between gap-3"><span className="text-3xl font-semibold tabular-nums">{completion.percentage}%</span><span className="text-xs text-muted-foreground">{completion.completed} of {completion.total} checks complete</span></div><Progress value={completion.percentage} className="mt-3" /><p className="mt-3 text-xs leading-5 text-muted-foreground">This is the current backend completion score; optional sections are not individually scored unless the backend includes them.</p></> : <p className="text-sm text-muted-foreground">Profile completion is unavailable right now.</p>}</CardContent></Card>
            <Card className="shadow-none"><CardHeader><CardTitle className="text-base">Your information stays yours</CardTitle></CardHeader><CardContent className="space-y-3 text-sm text-muted-foreground"><p>Student-entered education records are not institution-verified by default.</p><Separator /><p>Uploading a CV stores it in your Kairos documents. Automatic extraction and field-by-field CV review are not yet supported by the current backend.</p><Button variant="outline" className="w-full gap-2" onClick={() => openDrawer("resumes")}>Manage resumes <ArrowUpRight className="h-4 w-4" /></Button></CardContent></Card>
          </div>
        </div>
      )}

      <Sheet open={drawerOpen} onOpenChange={(open) => { if (!open && (saving || uploading)) return; setDrawerOpen(open); if (!open) { setError(""); setNotice(""); } }}>
        <SheetContent side="right" showCloseButton={false} className="w-full gap-0 overflow-hidden p-0 sm:max-w-5xl">
          <SheetHeader className="border-b px-5 py-5 sm:px-7">
            <div className="flex items-start justify-between gap-4 pr-8">
              <div><SheetTitle className="text-xl">Build your student profile</SheetTitle><SheetDescription className="mt-1 max-w-2xl">Upload your CV or add your details manually. You stay in control of what gets saved.</SheetDescription></div>
              <Button variant="ghost" size="icon" aria-label="Close profile drawer" onClick={() => setDrawerOpen(false)} disabled={saving || uploading}><X className="h-4 w-4" /></Button>
            </div>
            {completion && <div className="mt-4 flex items-center gap-3"><Progress value={completion.percentage} className="h-2 flex-1" /><span className="text-xs tabular-nums text-muted-foreground">{completion.percentage}% complete</span></div>}
          </SheetHeader>
          <div className="flex min-h-0 flex-1 flex-col md:flex-row">
            <nav aria-label="Profile sections" className="flex shrink-0 gap-1 overflow-x-auto border-b p-2 md:w-60 md:flex-col md:overflow-y-auto md:border-b-0 md:border-r md:p-3">
              {sections.map((section) => { const Icon = section.icon; return <button key={section.id} onClick={() => { setActiveSection(section.id); setError(""); setNotice(""); }} aria-current={activeSection === section.id ? "step" : undefined} className={`flex min-w-max items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:min-w-0 ${activeSection === section.id ? "bg-teal-50 font-medium text-teal-900 dark:bg-teal-950/50 dark:text-teal-100" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}><Icon className="h-4 w-4 shrink-0" /><span>{section.label}</span></button>; })}
            </nav>
            <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6 md:p-7">
              {error && <div role="alert" className="mb-4 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
              {notice && <div role="status" className="mb-4 flex items-start gap-2 rounded-lg border border-teal-600/20 bg-teal-50 p-3 text-sm text-teal-900 dark:bg-teal-950/30 dark:text-teal-100"><Check className="mt-0.5 h-4 w-4 shrink-0" />{notice}</div>}
              <div className="mb-5"><h2 className="text-lg font-semibold">{selected.label}</h2><p className="mt-1 text-sm text-muted-foreground">{selected.description}</p></div>

              {activeSection === "personal" && <form id="personal-profile-form" onSubmit={persistPersonal} className="max-w-2xl space-y-5">
                <div className="rounded-xl border bg-muted/20 p-4 text-sm text-muted-foreground">Your name and phone number are saved to your authenticated account. Email and enrollment details are read-only here.</div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2"><Label htmlFor="student-full-name">Full name</Label><Input id="student-full-name" value={fullName} onChange={(event) => setFullName(event.target.value)} maxLength={255} required /></div>
                  <div className="space-y-2"><Label htmlFor="student-email">Account email</Label><Input id="student-email" value={cv?.profile.email ?? account.email} readOnly disabled /></div>
                  <div className="space-y-2 sm:col-span-2"><Label htmlFor="student-phone">Phone number</Label><Input id="student-phone" value={phone} onChange={(event) => setPhone(event.target.value)} maxLength={32} placeholder="Add a contact number (optional)" /></div>
                </div>
                <div className="flex justify-end"><Button type="submit" disabled={saving || !dirtyPersonal} className="gap-2">{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save personal information</Button></div>
              </form>}

              {activeSection === "academics" && <div className="space-y-6">
                <form onSubmit={saveAcademic} className="space-y-4 rounded-xl border p-4 sm:p-5">
                  <div><h3 className="font-medium">{editingAcademicId ? "Edit education record" : "Add education"}</h3><p className="mt-1 text-xs text-muted-foreground">Required: institution and qualification. Grades are saved exactly as you enter them.</p></div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    {([["institution_name","Institution"],["qualification","Degree / qualification"],["field_of_study","Field of study"],["semester","Semester (if applicable)"],["start_date","Start date"],["end_date","End date"],["grade_value","Grade / result"],["grade_max","Maximum grade"],["grading_scale","Grading scale"]] as const).map(([key,label]) => <div key={key} className="space-y-2"><Label htmlFor={`academic-${key}`}>{label}</Label><Input id={`academic-${key}`} type={key.endsWith("_date") ? "date" : key === "grade_value" || key === "grade_max" ? "number" : "text"} step={key === "grade_value" || key === "grade_max" ? "any" : undefined} min={key === "grade_value" || key === "grade_max" ? "0" : undefined} value={academicForm[key]} onChange={(event) => setAcademicForm((current) => ({ ...current, [key]: event.target.value }))} /></div>)}
                    <div className="space-y-2 sm:col-span-2"><Label htmlFor="academic-description">Notes / relevant coursework</Label><Textarea id="academic-description" value={academicForm.description} onChange={(event) => setAcademicForm((current) => ({ ...current, description: event.target.value }))} maxLength={10000} rows={3} /></div>
                  </div>
                  <div className="flex flex-wrap justify-end gap-2">{editingAcademicId && <Button type="button" variant="outline" onClick={() => { setEditingAcademicId(null); setAcademicForm({ ...blankAcademic }); }}>Cancel edit</Button>}<Button type="submit" disabled={saving} className="gap-2">{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}{editingAcademicId ? "Save education" : "Add education"}</Button></div>
                </form>
                <div className="space-y-3">{(cv?.academics ?? []).length ? cv!.academics.map((item) => <Card key={item.id} className="shadow-none"><CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h3 className="font-medium">{item.qualification}</h3><Badge variant={item.is_verified ? "default" : "outline"}>{item.is_verified ? "Institution verified" : "Student-entered"}</Badge></div><p className="mt-1 text-sm text-muted-foreground">{item.institution_name}{item.field_of_study ? ` · ${item.field_of_study}` : ""}</p><p className="mt-2 text-xs text-muted-foreground">{dateText(item.start_date)}{item.end_date ? ` – ${dateText(item.end_date)}` : ""}{item.semester ? ` · ${item.semester}` : ""}</p>{item.grade_value != null && <p className="mt-2 text-sm">Result: {item.grade_value}{item.grade_max != null ? ` / ${item.grade_max}` : ""}{item.grading_scale ? ` (${item.grading_scale})` : ""}</p>}</div><div className="flex shrink-0 gap-2"><Button size="sm" variant="outline" onClick={() => beginEditAcademic(item)}>Edit</Button><Button size="icon" variant="ghost" aria-label={`Delete ${item.qualification}`} onClick={() => void removeAcademic(item.id)}><Trash2 className="h-4 w-4" /></Button></div></CardContent></Card>) : <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">No education records yet. Add one above whenever you’re ready.</p>}</div>
              </div>}

              {collections.includes(activeSection as PortfolioKind) && <div className="space-y-6">
                <form onSubmit={saveEntry} className="space-y-4 rounded-xl border p-4 sm:p-5">
                  <div><h3 className="font-medium">{editingEntryId ? "Edit entry" : `Add ${selected.label.toLowerCase()}`}</h3><p className="mt-1 text-xs text-muted-foreground">Only enter information you can stand behind. Leave optional fields blank when they do not apply.</p></div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2 sm:col-span-2"><Label htmlFor="entry-title">Title / name <span className="text-destructive">*</span></Label><Input id="entry-title" value={entryForm.title} onChange={(event) => setEntryForm((current) => ({ ...current, title: event.target.value }))} required maxLength={255} /></div>
                    <div className="space-y-2"><Label htmlFor="entry-organization">{entryKind === "skills" ? "Category / context" : entryKind === "certifications" ? "Issuing organization" : "Organization"}</Label><Input id="entry-organization" value={entryForm.organization} onChange={(event) => setEntryForm((current) => ({ ...current, organization: event.target.value }))} maxLength={255} /></div>
                    {entryKind === "skills" && <div className="space-y-2"><Label htmlFor="entry-proficiency">Self-reported proficiency (optional)</Label><Input id="entry-proficiency" value={entryForm.proficiency} onChange={(event) => setEntryForm((current) => ({ ...current, proficiency: event.target.value }))} maxLength={64} placeholder="e.g. Beginner, Intermediate" /></div>}
                    <div className="space-y-2"><Label htmlFor="entry-start-date">Start date</Label><Input id="entry-start-date" type="date" value={entryForm.start_date} onChange={(event) => setEntryForm((current) => ({ ...current, start_date: event.target.value }))} /></div>
                    <div className="space-y-2"><Label htmlFor="entry-end-date">{entryKind === "certifications" ? "Expiry / end date" : "End date"}</Label><Input id="entry-end-date" type="date" min={entryForm.start_date || undefined} value={entryForm.end_date} onChange={(event) => setEntryForm((current) => ({ ...current, end_date: event.target.value }))} /></div>
                    {entryKind === "certifications" && <div className="space-y-2"><Label htmlFor="entry-issued-date">Issue date</Label><Input id="entry-issued-date" type="date" value={entryForm.issued_date} onChange={(event) => setEntryForm((current) => ({ ...current, issued_date: event.target.value }))} /></div>}
                    <div className="space-y-2 sm:col-span-2"><Label htmlFor="entry-url">Link (optional)</Label><Input id="entry-url" type="url" placeholder="https://" value={entryForm.url} onChange={(event) => setEntryForm((current) => ({ ...current, url: event.target.value }))} maxLength={2048} /></div>
                    {entryKind === "certifications" && <div className="space-y-2 sm:col-span-2"><Label htmlFor="entry-credential">Credential ID (optional)</Label><Input id="entry-credential" value={entryForm.credential_id} onChange={(event) => setEntryForm((current) => ({ ...current, credential_id: event.target.value }))} maxLength={255} /></div>}
                    <div className="space-y-2 sm:col-span-2"><Label htmlFor="entry-description">Description / contribution</Label><Textarea id="entry-description" rows={4} value={entryForm.description} onChange={(event) => setEntryForm((current) => ({ ...current, description: event.target.value }))} maxLength={10000} placeholder="What did you work on? What was your contribution?" /></div>
                  </div>
                  <div className="flex flex-wrap justify-end gap-2">{editingEntryId && <Button type="button" variant="outline" onClick={() => { setEditingEntryId(null); setEntryForm({ ...blankEntry }); }}>Cancel edit</Button>}<Button type="submit" disabled={saving} className="gap-2">{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}{editingEntryId ? "Save changes" : "Add entry"}</Button></div>
                </form>
                <div className="space-y-3">{entriesFor(activeSection as PortfolioKind).length ? entriesFor(activeSection as PortfolioKind).map((item) => <Card key={item.id} className="shadow-none"><CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0"><h3 className="font-medium">{item.title}</h3>{item.organization && <p className="mt-1 text-sm text-muted-foreground">{item.organization}</p>}{item.description && <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{item.description}</p>}<p className="mt-2 text-xs text-muted-foreground">{dateText(item.start_date)}{item.end_date ? ` – ${dateText(item.end_date)}` : ""}{item.proficiency ? ` · ${item.proficiency}` : ""}</p>{item.url && <a href={item.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-sm text-teal-700 underline underline-offset-4 dark:text-teal-300">Open link <ArrowUpRight className="h-3 w-3" /></a>}</div><div className="flex shrink-0 gap-2"><Button size="sm" variant="outline" onClick={() => beginEditEntry(activeSection as PortfolioKind, item)}>Edit</Button><Button size="icon" variant="ghost" aria-label={`Delete ${item.title}`} onClick={() => void removeEntry(activeSection as PortfolioKind, item.id)}><Trash2 className="h-4 w-4" /></Button></div></CardContent></Card>) : <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">Nothing here yet. You can add your first entry above.</p>}</div>
              </div>}

              {activeSection === "resumes" && <div className="space-y-5">
                <div onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={onDrop} className={`rounded-2xl border-2 border-dashed p-6 text-center transition-colors sm:p-9 ${dragging ? "border-teal-600 bg-teal-50/70 dark:bg-teal-950/30" : "border-border bg-muted/20"}`}>
                  <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border bg-background text-teal-700 dark:text-teal-300"><UploadCloud className="h-6 w-6" /></span>
                  <h3 className="mt-4 font-medium">{uploading ? "Uploading your CV…" : "Drop your CV here"}</h3>
                  <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">PDF or plain-text files, up to 10 MiB. Your file is stored and attached to your profile; Kairos does not currently extract profile fields from it.</p>
                  <input ref={fileRef} type="file" accept=".pdf,.txt,application/pdf,text/plain" className="sr-only" aria-label="Choose a CV file" onChange={(event: ChangeEvent<HTMLInputElement>) => void uploadFile(event.target.files?.[0])} />
                  <Button type="button" variant="outline" className="mt-4 gap-2" disabled={uploading} onClick={() => fileRef.current?.click()}>{uploading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />} Choose file</Button>
                </div>
                <div className="rounded-lg border border-amber-600/20 bg-amber-50/70 p-3 text-sm text-amber-950 dark:bg-amber-950/20 dark:text-amber-100"><p className="font-medium">Extraction is not enabled</p><p className="mt-1 text-xs leading-5">No extracted data will be fabricated. You can add the information from your CV manually in the other sections.</p></div>
                <div className="space-y-3">{resumes.length ? resumes.map((resume) => <Card key={resume.id} className="shadow-none"><CardContent className="flex items-center gap-3 p-4"><FileText className="h-5 w-5 shrink-0 text-teal-700 dark:text-teal-300" /><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{resume.label}</p><p className="mt-1 text-xs text-muted-foreground">Attached {dateText(resume.created_at)}{resume.is_primary ? " · Primary resume" : ""}</p></div><Badge variant="outline">Attached</Badge><Button size="icon" variant="ghost" aria-label={`Remove ${resume.label}`} disabled={uploading} onClick={() => void removeResume(resume)}><Trash2 className="h-4 w-4" /></Button></CardContent></Card>) : <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">No resumes attached yet.</p>}</div>
              </div>}
            </div>
          </div>
          <SheetFooter className="border-t px-5 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-7">
            <p className="text-xs text-muted-foreground">{saving || uploading ? "Working… please keep this panel open." : dirtyPersonal ? "Personal information has unsaved changes." : "Changes are saved when you choose a save action."}</p>
            <div className="flex gap-2"><Button variant="outline" onClick={() => setDrawerOpen(false)} disabled={saving || uploading}>Close</Button>{activeSection === "personal" && <Button type="submit" form="personal-profile-form" disabled={saving || !dirtyPersonal} className="gap-2">{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save profile</Button>}</div>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </main>
  );
}
