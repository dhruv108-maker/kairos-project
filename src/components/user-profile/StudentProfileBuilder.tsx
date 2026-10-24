import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from "react";
import {
  AlertCircle, ArrowUpRight, BookOpen, BriefcaseBusiness, Check, ChevronRight,
  FileText, GraduationCap, Link2, LoaderCircle, Plus, Save, Trash2, UploadCloud,
  UserRound, Wrench,
} from "lucide-react";
import { apiRequest, ApiError } from "@/api/kairos-client";
import { useAuth } from "@/context/auth/AuthContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
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
    setActiveSection(kind); setDrawerOpen(true); setError(""); setNotice(""); setEntryKind(kind); setEditingEntryId(entry.id);
    setEntryForm(Object.fromEntries(Object.keys(blankEntry).map((key) => [key, String(entry[key as keyof PortfolioEntry] ?? "")])) as typeof blankEntry);
  };
  const beginEditAcademic = (item: AcademicEntry) => {
    setActiveSection("academics"); setDrawerOpen(true); setError(""); setNotice(""); setEditingAcademicId(item.id);
    setAcademicForm(Object.fromEntries(Object.keys(blankAcademic).map((key) => [key, String(item[key as keyof AcademicEntry] ?? "")])) as typeof blankAcademic);
  };

  if (!account?.roles.some((role) => role.toUpperCase() === "STUDENT")) {
    return <div className="mx-auto max-w-4xl p-6"><Card><CardContent className="p-6 text-sm text-muted-foreground">The student profile builder is available to authenticated student accounts.</CardContent></Card></div>;
  }

  return (
    <main className="mx-auto w-full max-w-[1440px] space-y-6 px-4 pb-12 pt-5 sm:px-6 lg:px-8">
      <div className="flex items-center gap-2 text-sm text-muted-foreground"><span>Dashboard</span><ChevronRight className="h-3.5 w-3.5" /><span className="font-medium text-foreground">My Profile</span></div>
      <header className="flex flex-col justify-between gap-4 border-b pb-6 md:flex-row md:items-end">
        <div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-teal-700 dark:text-teal-300">KAIROS · STUDENT SPACE</p><h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Your profile, your story.</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">Build a professional profile that reflects your academic journey, skills, and experience.</p></div>
        <div className="flex flex-wrap gap-2"><Button variant="outline" className="gap-2" onClick={() => openDrawer("resumes")}><UploadCloud className="h-4 w-4" /> Upload / manage CV</Button><Button className="gap-2" onClick={() => openDrawer("personal")}><UserRound className="h-4 w-4" /> Edit profile</Button></div>
      </header>
      {error && <div role="alert" className="flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
      {notice && <div role="status" className="flex items-start gap-2 rounded-xl border border-teal-700/20 bg-teal-50 p-4 text-sm text-teal-950 dark:bg-teal-950/30 dark:text-teal-100"><Check className="mt-0.5 h-4 w-4 shrink-0" />{notice}</div>}
      {!account?.roles.some((role) => role.toUpperCase() === "STUDENT") ? <Card className="shadow-none"><CardContent className="p-6 text-sm text-muted-foreground">The student profile is available to authenticated student accounts. Please sign in with an account that has the student role.</CardContent></Card> : loading ? <Card className="shadow-none"><CardContent className="space-y-4 p-6"><div className="h-6 w-48 animate-pulse rounded bg-muted" /><div className="h-4 w-3/4 animate-pulse rounded bg-muted" /><div className="h-24 animate-pulse rounded bg-muted/60" /></CardContent></Card> : drawerOpen ? (
        <section className="space-y-5">
          <div className="flex flex-col justify-between gap-4 border-b pb-5 sm:flex-row sm:items-center"><div><p className="text-xs font-semibold uppercase tracking-wider text-teal-700 dark:text-teal-300">PROFILE EDITOR</p><h2 className="mt-1 text-2xl font-semibold">{selected.label}</h2><p className="mt-1 text-sm text-muted-foreground">{selected.description}</p></div><Button variant="outline" onClick={() => { setDrawerOpen(false); setError(""); setNotice(""); }} disabled={saving || uploading}>Back to profile</Button></div>
          <div className="grid gap-5 xl:grid-cols-[220px_minmax(0,1fr)]">
            <nav aria-label="Profile sections" className="flex gap-1 overflow-x-auto rounded-xl border bg-card p-2 xl:flex-col">{sections.map((section) => { const Icon = section.icon; return <button key={section.id} onClick={() => { setActiveSection(section.id); setError(""); setNotice(""); }} className={"flex min-w-max items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted " + (activeSection === section.id ? "bg-teal-50 font-medium text-teal-950 dark:bg-teal-950/40 dark:text-teal-100" : "text-muted-foreground")}><Icon className="h-4 w-4" />{section.label}</button>; })}</nav>
            <div className="min-w-0 space-y-5">
              {activeSection === "personal" && <Card className="shadow-none"><CardHeader><CardTitle>Personal information</CardTitle><CardDescription>Only supported account fields are editable. Account email remains read-only.</CardDescription></CardHeader><CardContent><form id="personal-profile-form" onSubmit={persistPersonal} className="space-y-5"><div className="grid gap-5 md:grid-cols-2"><div className="space-y-2"><Label htmlFor="student-full-name">Full name</Label><Input id="student-full-name" value={fullName} onChange={(event) => setFullName(event.target.value)} maxLength={255} required className="h-11" /></div><div className="space-y-2"><Label htmlFor="student-email">Account email</Label><Input id="student-email" value={cv?.profile.email ?? account.email} readOnly disabled className="h-11" /></div><div className="space-y-2 md:col-span-2"><Label htmlFor="student-phone">Phone number (optional)</Label><Input id="student-phone" value={phone} onChange={(event) => setPhone(event.target.value)} maxLength={32} placeholder="Add a contact number" className="h-11" /></div></div><div className="flex justify-end"><Button type="submit" disabled={saving || !dirtyPersonal} className="gap-2">{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save changes</Button></div></form></CardContent></Card>}
              {activeSection === "academics" && <div className="space-y-5"><Card className="shadow-none"><CardHeader><CardTitle>{editingAcademicId ? "Edit education" : "Add education"}</CardTitle><CardDescription>Student-entered records are distinguished from institution-verified records.</CardDescription></CardHeader><CardContent><form onSubmit={saveAcademic} className="space-y-5"><div className="grid gap-5 md:grid-cols-2"><div className="space-y-2"><Label htmlFor="academic-institution">Institution *</Label><Input id="academic-institution" value={academicForm.institution_name} onChange={(event) => setAcademicForm((current) => ({ ...current, institution_name: event.target.value }))} required className="h-11" /></div><div className="space-y-2"><Label htmlFor="academic-qualification">Degree / qualification *</Label><Input id="academic-qualification" value={academicForm.qualification} onChange={(event) => setAcademicForm((current) => ({ ...current, qualification: event.target.value }))} required className="h-11" /></div>{([["field_of_study","Field of study"],["semester","Semester"],["start_date","Start date"],["end_date","End date"],["grade_value","Grade / result"],["grade_max","Maximum grade"],["grading_scale","Grading scale"]] as const).map(([key,label]) => <div key={key} className="space-y-2"><Label htmlFor={"academic-" + key}>{label}</Label><Input id={"academic-" + key} type={key.endsWith("_date") ? "date" : key === "grade_value" || key === "grade_max" ? "number" : "text"} value={academicForm[key]} onChange={(event) => setAcademicForm((current) => ({ ...current, [key]: event.target.value }))} className="h-11" /></div>)}<div className="space-y-2 md:col-span-2"><Label htmlFor="academic-description">Notes / relevant coursework</Label><Textarea id="academic-description" value={academicForm.description} onChange={(event) => setAcademicForm((current) => ({ ...current, description: event.target.value }))} rows={4} /></div></div><div className="flex justify-end gap-2">{editingAcademicId && <Button type="button" variant="outline" onClick={() => { setEditingAcademicId(null); setAcademicForm({ ...blankAcademic }); }}>Cancel edit</Button>}<Button type="submit" disabled={saving} className="gap-2">{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}{editingAcademicId ? "Save education" : "Add education"}</Button></div></form></CardContent></Card>{(cv?.academics ?? []).map((item) => <Card key={item.id} className="shadow-none"><CardContent className="flex flex-col justify-between gap-3 p-5 sm:flex-row"><div><div className="flex flex-wrap items-center gap-2"><h3 className="font-medium">{item.qualification}</h3><Badge variant={item.is_verified ? "default" : "outline"}>{item.is_verified ? "Institution verified" : "Student-entered"}</Badge></div><p className="mt-1 text-sm text-muted-foreground">{item.institution_name}{item.field_of_study ? " · " + item.field_of_study : ""}</p><p className="mt-2 text-xs text-muted-foreground">{dateText(item.start_date)}{item.end_date ? " – " + dateText(item.end_date) : ""}</p>{item.grade_value != null && <p className="mt-2 text-sm">Result: {item.grade_value}{item.grade_max != null ? " / " + item.grade_max : ""}</p>}</div><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => beginEditAcademic(item)}>Edit</Button><Button size="icon" variant="ghost" aria-label={"Delete " + item.qualification} onClick={() => void removeAcademic(item.id)}><Trash2 className="h-4 w-4" /></Button></div></CardContent></Card>)}</div>}
              {collections.includes(activeSection as PortfolioKind) && <div className="space-y-5"><Card className="shadow-none"><CardHeader><CardTitle>{editingEntryId ? "Edit entry" : "Add " + selected.label.toLowerCase()}</CardTitle><CardDescription>Keep details accurate and leave optional fields blank when they do not apply.</CardDescription></CardHeader><CardContent><form onSubmit={saveEntry} className="space-y-5"><div className="grid gap-5 md:grid-cols-2"><div className="space-y-2 md:col-span-2"><Label htmlFor="entry-title">Title / name *</Label><Input id="entry-title" value={entryForm.title} onChange={(event) => setEntryForm((current) => ({ ...current, title: event.target.value }))} required maxLength={255} className="h-11" /></div><div className="space-y-2"><Label htmlFor="entry-organization">Organization / context</Label><Input id="entry-organization" value={entryForm.organization} onChange={(event) => setEntryForm((current) => ({ ...current, organization: event.target.value }))} maxLength={255} className="h-11" /></div>{activeSection === "skills" && <div className="space-y-2"><Label htmlFor="entry-proficiency">Self-reported proficiency (optional)</Label><Input id="entry-proficiency" value={entryForm.proficiency} onChange={(event) => setEntryForm((current) => ({ ...current, proficiency: event.target.value }))} maxLength={64} className="h-11" /></div>}<div className="space-y-2"><Label htmlFor="entry-start-date">Start date</Label><Input id="entry-start-date" type="date" value={entryForm.start_date} onChange={(event) => setEntryForm((current) => ({ ...current, start_date: event.target.value }))} className="h-11" /></div><div className="space-y-2"><Label htmlFor="entry-end-date">End date</Label><Input id="entry-end-date" type="date" value={entryForm.end_date} onChange={(event) => setEntryForm((current) => ({ ...current, end_date: event.target.value }))} className="h-11" /></div><div className="space-y-2 md:col-span-2"><Label htmlFor="entry-url">External link (optional)</Label><Input id="entry-url" type="url" placeholder="https://" value={entryForm.url} onChange={(event) => setEntryForm((current) => ({ ...current, url: event.target.value }))} maxLength={2048} className="h-11" /></div><div className="space-y-2 md:col-span-2"><Label htmlFor="entry-description">Description / contribution (optional)</Label><Textarea id="entry-description" rows={5} value={entryForm.description} onChange={(event) => setEntryForm((current) => ({ ...current, description: event.target.value }))} maxLength={10000} /></div></div><div className="flex justify-end gap-2">{editingEntryId && <Button type="button" variant="outline" onClick={() => { setEditingEntryId(null); setEntryForm({ ...blankEntry }); }}>Cancel edit</Button>}<Button type="submit" disabled={saving} className="gap-2">{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}{editingEntryId ? "Save changes" : "Add entry"}</Button></div></form></CardContent></Card>{entriesFor(activeSection as PortfolioKind).map((item) => <Card key={item.id} className="shadow-none"><CardContent className="flex flex-col justify-between gap-3 p-5 sm:flex-row"><div className="min-w-0"><h3 className="font-medium">{item.title}</h3>{item.organization && <p className="mt-1 text-sm text-muted-foreground">{item.organization}</p>}{item.description && <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{item.description}</p>}{item.url && <a href={item.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-sm text-teal-700 underline dark:text-teal-300">Open link <ArrowUpRight className="h-3 w-3" /></a>}</div><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => beginEditEntry(activeSection as PortfolioKind,item)}>Edit</Button><Button size="icon" variant="ghost" aria-label={"Delete " + item.title} onClick={() => void removeEntry(activeSection as PortfolioKind,item.id)}><Trash2 className="h-4 w-4" /></Button></div></CardContent></Card>)}</div>}
              {activeSection === "resumes" && <div className="space-y-5"><Card className="shadow-none"><CardHeader><CardTitle>Resume and CV</CardTitle><CardDescription>PDF or plain-text files, up to 10 MiB.</CardDescription></CardHeader><CardContent><div onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={onDrop} className={"rounded-xl border-2 border-dashed p-6 text-center sm:p-10 " + (dragging ? "border-teal-600 bg-teal-50/70" : "border-border bg-muted/20")}><UploadCloud className="mx-auto h-8 w-8 text-teal-700" /><h3 className="mt-3 font-semibold">{uploading ? "Uploading your CV…" : "Drop your CV here"}</h3><p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-muted-foreground">The document appears in your profile only after the server confirms it. Automatic extraction is not available in the current backend.</p><Button type="button" variant="outline" className="mt-4 gap-2" disabled={uploading} onClick={() => fileRef.current?.click()}><UploadCloud className="h-4 w-4" /> Choose file</Button></div><input ref={fileRef} type="file" accept=".pdf,.txt,application/pdf,text/plain" className="sr-only" aria-label="Choose a CV file" onChange={(event: ChangeEvent<HTMLInputElement>) => void uploadFile(event.target.files?.[0])} /></CardContent></Card>{resumes.map((resume) => <Card key={resume.id} className="shadow-none"><CardContent className="flex items-center gap-3 p-4"><FileText className="h-5 w-5 text-teal-700" /><div className="min-w-0 flex-1"><p className="break-words text-sm font-medium">{resume.label}</p><p className="mt-1 text-xs text-muted-foreground">Added {dateText(resume.created_at)}{resume.is_primary ? " · Primary resume" : ""}</p></div><Badge variant="outline">Attached</Badge><Button size="icon" variant="ghost" aria-label={"Remove " + resume.label} onClick={() => void removeResume(resume)}><Trash2 className="h-4 w-4" /></Button></CardContent></Card>)}{!resumes.length && <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">No resume attached yet. Upload a PDF or text CV to get started.</p>}</div>}
            </div>
          </div>
        </section>
      ) : (
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.9fr)_minmax(280px,0.85fr)]">
          <div className="min-w-0 space-y-5">
            <Card className="shadow-none"><CardContent className="p-5 sm:p-7"><div className="flex flex-col gap-5 sm:flex-row sm:items-start"><div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border bg-teal-50 text-xl font-semibold text-teal-950 dark:bg-teal-950/50 dark:text-teal-100">{(cv?.profile.full_name || account.full_name || "S").trim().split(/\s+/).slice(0,2).map((part) => part[0]?.toUpperCase()).join("") || "S"}</div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="text-xl font-semibold tracking-tight">{cv?.profile.full_name || account.full_name || "Add your name"}</h2><Badge variant="outline">Student profile</Badge></div><p className="mt-1 break-words text-sm text-muted-foreground">{cv?.profile.email || account.email}</p>{cv?.profile.phone_number && <p className="mt-1 text-sm text-muted-foreground">{cv.profile.phone_number}</p>}<p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground">Your profile brings together the information you choose to share about your education, skills, projects, and experience.</p><Button variant="outline" size="sm" className="mt-4 gap-2" onClick={() => openDrawer("personal")}><UserRound className="h-4 w-4" /> Edit personal information</Button></div></div><div className="mt-6 grid gap-3 border-t pt-5 sm:grid-cols-3"><div><p className="text-xs text-muted-foreground">Education records</p><p className="mt-1 text-2xl font-semibold tabular-nums">{cv?.academics.length ?? 0}</p></div><div><p className="text-xs text-muted-foreground">Skills listed</p><p className="mt-1 text-2xl font-semibold tabular-nums">{entriesFor("skills").length}</p></div><div><p className="text-xs text-muted-foreground">Resume documents</p><p className="mt-1 text-2xl font-semibold tabular-nums">{resumes.length}</p></div></div></CardContent></Card>
            <Card className="shadow-none"><CardHeader className="flex flex-row items-center justify-between gap-3"><div><CardTitle className="text-base">Education</CardTitle><CardDescription className="mt-1">Academic history and results, when available.</CardDescription></div><Button variant="outline" size="sm" onClick={() => openDrawer("academics")}><Plus className="mr-1 h-4 w-4" /> Add education</Button></CardHeader><CardContent>{cv?.academics.length ? cv.academics.map((item) => <div key={item.id} className="flex gap-3 border-t py-4 first:border-0 first:pt-0"><GraduationCap className="mt-1 h-4 w-4 shrink-0 text-teal-700" /><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="font-medium">{item.qualification}</h3><Badge variant={item.is_verified ? "default" : "outline"}>{item.is_verified ? "Institution verified" : "Student-entered"}</Badge></div><p className="mt-1 text-sm text-muted-foreground">{item.institution_name}{item.field_of_study ? " · " + item.field_of_study : ""}</p><p className="mt-1 text-xs text-muted-foreground">{dateText(item.start_date)}{item.end_date ? " – " + dateText(item.end_date) : ""}</p>{item.grade_value != null && <p className="mt-2 text-sm">Result: {item.grade_value}{item.grade_max != null ? " / " + item.grade_max : ""}</p>}</div><Button size="icon" variant="ghost" aria-label={"Edit " + item.qualification} onClick={() => beginEditAcademic(item)}><Wrench className="h-4 w-4" /></Button></div>) : <div className="rounded-lg border border-dashed p-5 text-center"><p className="text-sm text-muted-foreground">No education records yet.</p><Button variant="link" onClick={() => openDrawer("academics")}>Add your education</Button></div>}</CardContent></Card>
            {(["skills","experience","projects","research","certifications","achievements"] as PortfolioKind[]).map((kind) => { const section = sections.find((item) => item.kind === kind)!; const Icon = section.icon; const items = entriesFor(kind); return <Card key={kind} className="shadow-none"><CardHeader className="flex flex-row items-start justify-between gap-3"><div className="flex gap-3"><div className="rounded-lg border bg-muted/30 p-2"><Icon className="h-4 w-4 text-teal-800" /></div><div><CardTitle className="text-base">{section.label}</CardTitle><CardDescription className="mt-1">{section.description}</CardDescription></div></div><Button variant="outline" size="sm" onClick={() => { setEntryKind(kind); setEntryForm({ ...blankEntry }); setEditingEntryId(null); openDrawer(kind); }}><Plus className="mr-1 h-4 w-4" /> Add</Button></CardHeader><CardContent>{items.length ? kind === "skills" ? <div className="flex flex-wrap gap-2">{items.map((item) => <button key={item.id} onClick={() => beginEditEntry(kind,item)} className="rounded-lg border bg-background px-3 py-2 text-sm font-medium transition-colors hover:border-teal-700/40 hover:bg-muted">{item.title}{item.proficiency ? <span className="ml-2 text-xs font-normal text-muted-foreground">{item.proficiency}</span> : null}</button>)}</div> : <div className="divide-y">{items.map((item) => <div key={item.id} className="flex flex-col gap-3 py-4 first:pt-0 sm:flex-row sm:items-start"><div className="min-w-0 flex-1"><h3 className="font-medium">{item.title}</h3>{item.organization && <p className="mt-1 text-sm text-muted-foreground">{item.organization}</p>}{item.description && <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{item.description}</p>}{item.url && <a href={item.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-sm text-teal-700 underline dark:text-teal-300">Open link <ArrowUpRight className="h-3 w-3" /></a>}</div><div className="flex gap-1"><Button size="icon" variant="ghost" aria-label={"Edit " + item.title} onClick={() => beginEditEntry(kind,item)}><Wrench className="h-4 w-4" /></Button><Button size="icon" variant="ghost" aria-label={"Delete " + item.title} onClick={() => void removeEntry(kind,item.id)}><Trash2 className="h-4 w-4" /></Button></div></div>)}</div> : <div className="rounded-lg border border-dashed p-5 text-center"><p className="text-sm text-muted-foreground">No {section.label.toLowerCase()} added yet.</p><Button variant="link" onClick={() => { setEntryKind(kind); setEntryForm({ ...blankEntry }); setEditingEntryId(null); openDrawer(kind); }}>Add your first entry</Button></div>}</CardContent></Card>; })}
          </div>
          <aside className="min-w-0 space-y-5"><Card className="shadow-none"><CardHeader className="pb-3"><CardTitle className="text-base">Profile completion</CardTitle><CardDescription>Based on the current Kairos completion service.</CardDescription></CardHeader><CardContent>{completion ? <><div className="flex items-end justify-between gap-3"><span className="text-3xl font-semibold tabular-nums">{completion.percentage}%</span><span className="text-xs text-muted-foreground">{completion.completed} of {completion.total} checks complete</span></div><Progress value={completion.percentage} className="mt-3" /><p className="mt-3 text-xs leading-5 text-muted-foreground">This score is provided by Kairos; optional sections are counted only when the backend includes them.</p></> : <p className="text-sm leading-6 text-muted-foreground">Completion data is unavailable right now. Your saved profile is still shown.</p>}</CardContent></Card>
            <Card className="shadow-none"><CardHeader className="pb-3"><CardTitle className="text-base">Resume / CV</CardTitle><CardDescription>Keep a current resume attached.</CardDescription></CardHeader><CardContent className="space-y-4">{resumes.length ? resumes.map((resume) => <div key={resume.id} className="flex items-start gap-3"><FileText className="mt-1 h-4 w-4 shrink-0 text-teal-700" /><div className="min-w-0 flex-1"><p className="break-words text-sm font-medium">{resume.label}</p><p className="mt-1 text-xs text-muted-foreground">{resume.is_primary ? "Primary resume · " : ""}{dateText(resume.created_at)}</p></div><Badge variant="outline">Attached</Badge></div>) : <p className="text-sm leading-6 text-muted-foreground">No resume attached yet. Upload a PDF or plain-text CV.</p>}<Button variant="outline" className="w-full gap-2" onClick={() => openDrawer("resumes")}><UploadCloud className="h-4 w-4" /> Manage resumes</Button><p className="text-xs leading-5 text-muted-foreground">Automatic CV extraction and field population are not available in the current backend.</p></CardContent></Card>
            <Card className="shadow-none"><CardHeader className="pb-3"><CardTitle className="text-base">Quick navigation</CardTitle></CardHeader><CardContent className="space-y-1 p-3 pt-0">{sections.filter((section) => section.id !== "personal").map((section) => { const Icon = section.icon; const count = section.kind === "academics" ? (cv?.academics.length ?? 0) : section.kind === "resumes" ? resumes.length : entriesFor(section.kind as PortfolioKind).length; return <button key={section.id} onClick={() => openDrawer(section.id)} className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted"><Icon className="h-4 w-4 text-muted-foreground" /><span className="min-w-0 flex-1">{section.label}</span><Badge variant="secondary">{count}</Badge></button>; })}</CardContent></Card>
          </aside>
        </div>
      )}
    </main>
  );
}
