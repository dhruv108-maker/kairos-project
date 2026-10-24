import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { ArrowRight, CheckCircle2, Eye, EyeOff, GraduationCap, LockKeyhole, Mail, UsersRound } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import AuthFrame from "@/components/auth/AuthFrame";
import { apiRequest } from "@/api/kairos-client";

type RegistrationRole = "student" | "faculty";

interface InstitutionOption { id: string; name: string; }
interface InstitutionResolution { status: "matched" | "ambiguous" | "not_found"; institution: InstitutionOption | null; }
interface AcademicOptions { schools: Array<{ id: string; name: string; code: string }>; departments: Array<{ id: string; name: string; code: string; school_id: string }>; programmes: Array<{ id: string; name: string; code: string; degree_level: string; department_id: string }>; cohorts: Array<{ id: string; name: string; programme_name: string; department_name: string; academic_year: string; graduation_year: number }>; }

interface RegistrationResponse {
  account_id: string;
  message: string;
  verification_email_sent: boolean;
  activation_pending: boolean;
}

const BoxedRegister = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [role, setRole] = useState<RegistrationRole>(searchParams.get("role") === "faculty" ? "faculty" : "student");
  const [email, setEmail] = useState("");
  const [institutionId, setInstitutionId] = useState("");
  const [institutionName, setInstitutionName] = useState("");
  const [verifiedDomainMatch, setVerifiedDomainMatch] = useState(false);
  const [institutionSearch, setInstitutionSearch] = useState("");
  const [institutions, setInstitutions] = useState<InstitutionOption[]>([]);
  const [institutionStatus, setInstitutionStatus] = useState<"idle" | "loading" | "matched" | "fallback" | "error">("idle");
  const [showInstitutionPicker, setShowInstitutionPicker] = useState(false);
  const [academicOptions, setAcademicOptions] = useState<AcademicOptions>({ schools: [], departments: [], programmes: [], cohorts: [] });
  const [schoolId, setSchoolId] = useState("");
  const [academicOptionsLoading, setAcademicOptionsLoading] = useState(false);
  const [academicOptionsError, setAcademicOptionsError] = useState(false);
  const [academicOptionsErrorMessage, setAcademicOptionsErrorMessage] = useState("");
  const [academicOptionsRetry, setAcademicOptionsRetry] = useState(0);
  const [departmentId, setDepartmentId] = useState("");
  const [programmeId, setProgrammeId] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [verificationSent, setVerificationSent] = useState(false);
  const [activationPending, setActivationPending] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const emailDomain = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())
    ? email.trim().toLowerCase().split("@").pop() ?? ""
    : "";
  const selectedDepartments = academicOptions.departments.filter((department) => department.school_id === schoolId);
  const selectedProgrammes = academicOptions.programmes.filter((programme) => programme.department_id === departmentId);

  useEffect(() => {
    if (!emailDomain) {
      setInstitutionId(""); setInstitutionName(""); setInstitutionStatus("idle"); setVerifiedDomainMatch(false); setShowInstitutionPicker(false);
      return;
    }
    setInstitutionId("");
    setInstitutionName("");
    setVerifiedDomainMatch(false);
    setInstitutionStatus("loading");
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const result = await apiRequest<InstitutionResolution>("/institutions/resolve?email_domain=" + encodeURIComponent(emailDomain));
        if (cancelled) return;
        if (result.status === "matched" && result.institution) {
          setInstitutionId(result.institution.id); setInstitutionName(result.institution.name); setVerifiedDomainMatch(true); setInstitutionStatus("matched"); setShowInstitutionPicker(false);
        } else {
          setInstitutionId(""); setInstitutionName(""); setVerifiedDomainMatch(false); setInstitutionStatus("fallback"); setShowInstitutionPicker(true);
        }
      } catch {
        if (cancelled) return;
        setInstitutionId(""); setInstitutionName(""); setVerifiedDomainMatch(false); setInstitutionStatus("error"); setShowInstitutionPicker(true);
      }
    }, 350);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [emailDomain]);

  useEffect(() => {
    if (!showInstitutionPicker) return;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const q = institutionSearch.trim();
        const result = await apiRequest<{ items: InstitutionOption[] }>("/institutions/public" + (q ? "?q=" + encodeURIComponent(q) : ""));
        if (!cancelled) setInstitutions(result.items);
      } catch { if (!cancelled) setInstitutions([]); }
    }, 200);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [showInstitutionPicker, institutionSearch]);

  useEffect(() => {
  }, [email]);

  useEffect(() => {
    setAcademicOptions({ schools: [], departments: [], programmes: [], cohorts: [] });
    setSchoolId("");
    setDepartmentId("");
    setProgrammeId("");
    setAcademicOptionsError(false);
    setAcademicOptionsErrorMessage("");

    // Public enrollment choices are available only after an exact verified-domain match.
    if (!institutionId || !verifiedDomainMatch) {
      setAcademicOptionsLoading(false);
      return;
    }

    let cancelled = false;
    setAcademicOptionsLoading(true);
    apiRequest<AcademicOptions>("/institutions/public/" + encodeURIComponent(institutionId) + "/academic-options")
      .then((result) => {
        if (cancelled) return;
        setAcademicOptions(result);
        setSchoolId((selected) => result.schools.some((school) => school.id === selected) ? selected : "");
        setDepartmentId((selected) => result.departments.some((department) => department.id === selected && department.school_id === schoolId) ? selected : "");
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setAcademicOptions({ schools: [], departments: [], programmes: [], cohorts: [] });
          setSchoolId("");
          setDepartmentId("");
          setProgrammeId("");
          setAcademicOptionsError(true);
          setAcademicOptionsErrorMessage(err instanceof Error ? err.message : "The academic options service is unavailable.");
        }
      })
      .finally(() => { if (!cancelled) setAcademicOptionsLoading(false); });
    return () => { cancelled = true; };
  }, [institutionId, verifiedDomainMatch, academicOptionsRetry]);
  const handleRoleChange = (nextRole: RegistrationRole) => {
    setRole(nextRole);
    setSchoolId("");
    setDepartmentId("");
    setProgrammeId("");
    setError("");
    setMessage("");
    setVerificationSent(false);
    setActivationPending(false);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) return;
    setError("");
    setMessage("");

    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const submittedEmail = String(form.get("email") ?? "").trim().toLowerCase();
    const password = String(form.get("password") ?? "");
    const confirmPassword = String(form.get("confirm_password") ?? "");
    const fullName = String(form.get("full_name") ?? "").trim();

    if (password.length < 12 || password.length > 128) {
      setError("Choose a password between 12 and 128 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("The passwords do not match. Please check and try again.");
      return;
    }
    if (!fullName || !submittedEmail) {
      setError("Enter your name and a valid email address to continue.");
      return;
    }

    if (!institutionId) { setError("Select your institution before continuing."); return; }
    if (!verifiedDomainMatch) { setError("Your institution email domain is not verified. Contact your institution administrator to verify it before registering."); return; }
    if (academicOptionsLoading || academicOptionsError || !academicOptions.schools.some((school) => school.id === schoolId)) {
      setError("Choose an available school for your verified institution.");
      return;
    }
    if (!academicOptions.departments.some((department) => department.id === departmentId && department.school_id === schoolId)) {
      setError("Choose a department within your selected school.");
      return;
    }

    if (role === "student" && !academicOptions.programmes.some((programme) => programme.id === programmeId && programme.department_id === departmentId)) {
      setError("Choose a programme within your selected department.");
      return;
    }

    const common = { email: submittedEmail, password, full_name: fullName, institution_id: institutionId };
    const payload = role === "student"
      ? {
          ...common,
          enrollment_number: String(form.get("enrollment_number") ?? "").trim(),
          school_id: schoolId,
          department_id: departmentId,
          programme_id: programmeId,
        }
      : {
          ...common,
          employee_code: String(form.get("employee_code") ?? "").trim(),
          school_id: schoolId,
          department_id: departmentId,
          designation: String(form.get("designation") ?? "").trim(),
        };

    setIsSubmitting(true);
    try {
      const result = await apiRequest<RegistrationResponse>(`/auth/register/${role}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setRegisteredEmail(submittedEmail);
      setMessage(result.message);
      setVerificationSent(result.verification_email_sent);
      setActivationPending(result.activation_pending);
      formElement.reset();
      setShowPassword(false);
      setShowConfirmPassword(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please review your details and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const resendVerification = async () => {
    if (!registeredEmail || isResending) return;
    setError("");
    setIsResending(true);
    try {
      const result = await apiRequest<{ message: string }>("/auth/verification/resend", {
        method: "POST",
        body: JSON.stringify({ email: registeredEmail }),
      });
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to request another verification email.");
    } finally {
      setIsResending(false);
    }
  };

  return (
    <AuthFrame
      asideEyebrow="Your academic community"
      asideTitle="One academic identity. A more connected experience."
      asideDescription="Create your account with the details your institution uses, then verify your email to get started."
      footer={<>Already have an account? <Link to="/auth/auth2/login" className="font-medium text-foreground underline underline-offset-4 hover:text-muted-foreground">Sign in</Link></>}
    >
      {message ? (
        <div className="min-w-0 space-y-5">
          <div className="flex size-12 items-center justify-center rounded-full border border-border bg-muted">
            <CheckCircle2 aria-hidden="true" className="size-6" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-muted-foreground">REGISTRATION RECEIVED</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Check your inbox</h1>
            <p className="mt-2 break-words text-sm leading-6 text-muted-foreground">{message}</p>
          </div>
          <Alert className="min-w-0">
            <Mail aria-hidden="true" className="size-4" />
            <AlertTitle>{verificationSent ? "Verification email sent" : "Email verification may still be needed"}</AlertTitle>
            <AlertDescription className="min-w-0 break-words">
              We’ll send instructions to <span className="break-all font-medium text-foreground">{registeredEmail}</span> when delivery is available. Check your spam folder too.
              {activationPending ? " Faculty access also requires institutional approval." : ""}
            </AlertDescription>
          </Alert>
          <Button type="button" variant="outline" className="h-11 w-full whitespace-normal" onClick={resendVerification} disabled={isResending}>
            {isResending ? "Requesting email…" : "Resend verification email"}
          </Button>
          <Button type="button" className="h-11 w-full whitespace-normal" onClick={() => navigate("/auth/auth2/login")}>Continue to sign in <ArrowRight aria-hidden="true" className="ml-2 size-4" /></Button>
          <button type="button" onClick={() => { setMessage(""); setError(""); setVerificationSent(false); setActivationPending(false); setEmail(""); setInstitutionId(""); setInstitutionName(""); setVerifiedDomainMatch(false); setInstitutionStatus("idle"); setShowInstitutionPicker(false); }} className="w-full text-center text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground">
            Register another account
          </button>
          {error && <Alert variant="destructive" role="alert" aria-live="polite" className="min-w-0 break-words"><AlertDescription>{error}</AlertDescription></Alert>}
        </div>
      ) : (
        <>
          <div className="mb-6 min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Create your account</p>
            <h1 className="mt-2 text-[1.8rem] font-semibold tracking-[-0.035em]">Get started with Kairos</h1>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">A few details to connect you to your academic community.</p>
          </div>

          <div className="mb-6 min-w-0 space-y-2">
            <p className="text-sm font-medium">I’m joining as a</p>
            <div className="grid min-w-0 grid-cols-2 gap-2" role="group" aria-label="Choose account type">
              <Button type="button" variant={role === "student" ? "default" : "outline"} className="h-10 min-w-0 px-2 text-sm" aria-pressed={role === "student"} onClick={() => handleRoleChange("student")}>
                <GraduationCap aria-hidden="true" className="mr-1.5 size-4 shrink-0 sm:mr-2" /> <span>Student</span>
              </Button>
              <Button type="button" variant={role === "faculty" ? "default" : "outline"} className="h-10 min-w-0 px-2 text-sm" aria-pressed={role === "faculty"} onClick={() => handleRoleChange("faculty")}>
                <UsersRound aria-hidden="true" className="mr-1.5 size-4 shrink-0 sm:mr-2" /> <span>Faculty</span>
              </Button>
            </div>
            <p className="break-words text-xs leading-5 text-muted-foreground">{role === "student" ? "Choose your school and department. Your cohort can be assigned later." : "Choose your school and department. Faculty access requires institutional approval."}</p>
          </div>

          <form className="min-w-0 space-y-4" onSubmit={handleSubmit}>
            <div className="min-w-0 space-y-2">
              <Label htmlFor="full_name">Full name</Label>
              <Input id="full_name" name="full_name" autoComplete="name" placeholder="Your full name" maxLength={255} required />
            </div>
            <div className="min-w-0 space-y-2">
              <Label htmlFor="email">Email address</Label>
              <div className="relative min-w-0">
                <Mail aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input id="email" name="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" autoCapitalize="none" spellCheck={false} placeholder="you@institution.edu" maxLength={255} required className="pl-10" />
              </div>
            </div>

            <div className="min-w-0 space-y-2">
              <Label>Institution</Label>
              {institutionStatus === "loading" ? <p className="text-sm text-muted-foreground" role="status">Checking institutional domain…</p> : null}
              {institutionStatus === "matched" && institutionName && !showInstitutionPicker ? (
                <div className="flex min-w-0 items-center gap-2 rounded-md border border-emerald-600/30 bg-emerald-600/5 px-3 py-2.5">
                  <CheckCircle2 aria-hidden="true" className="size-4 shrink-0 text-emerald-700" />
                  <span className="min-w-0 flex-1 truncate text-sm font-medium">{institutionName}</span>
                </div>
              ) : null}
              {institutionStatus === "fallback" ? <p className="text-xs text-muted-foreground">No verified domain match was found. You may search for your institution, but student registration requires its administrator to verify this email domain first.</p> : null}
              {institutionStatus === "error" ? <Alert variant="destructive"><AlertDescription>Lookup unavailable. Search and select your institution.</AlertDescription></Alert> : null}
              {showInstitutionPicker ? (
                <div className="space-y-2">
                  <Input id="institution-search" value={institutionSearch} onChange={(event) => setInstitutionSearch(event.target.value)} placeholder="Search active institutions…" autoComplete="off" />
                  <div className="max-h-48 overflow-y-auto rounded-md border p-1" role="listbox" aria-label="Institutions">
                    {institutions.length ? institutions.map((institution) => (
                      <Button key={institution.id} type="button" variant="ghost" role="option" aria-selected={institutionId === institution.id} onClick={() => { setInstitutionId(institution.id); setInstitutionName(institution.name); setVerifiedDomainMatch(false); setInstitutionStatus("matched"); setShowInstitutionPicker(false); setInstitutionSearch(""); }} className="flex h-auto w-full items-center justify-start rounded-sm px-3 py-2 text-left text-sm font-normal">
                        <span className="min-w-0 flex-1 truncate">{institution.name}</span>
                        {institutionId === institution.id ? <CheckCircle2 aria-hidden="true" className="ml-2 size-4" /> : null}
                      </Button>
                    )) : <p className="px-3 py-4 text-center text-sm text-muted-foreground">No active institutions found.</p>}
                  </div>
                </div>
              ) : null}
            </div>
            <div className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="min-w-0 space-y-2">
                <Label>School / Faculty</Label>
                <Select value={schoolId} onValueChange={(value) => { setSchoolId(value ?? ""); setDepartmentId(""); setProgrammeId(""); }} disabled={!verifiedDomainMatch || academicOptionsLoading || academicOptionsError || academicOptions.schools.length === 0} required>
                  <SelectTrigger className="h-11 w-full min-w-0" aria-label="School"><SelectValue placeholder={academicOptionsLoading ? "Loading schools…" : !verifiedDomainMatch ? "Verify your institution email first" : "Choose your school"} /></SelectTrigger>
                  <SelectContent>{academicOptions.schools.map((school) => <SelectItem key={school.id} value={school.id}>{school.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="min-w-0 space-y-2">
                <Label>Department</Label>
                <Select value={departmentId} onValueChange={(value) => { setDepartmentId(value ?? ""); setProgrammeId(""); }} disabled={!schoolId || academicOptionsLoading || academicOptionsError || selectedDepartments.length === 0} required>
                  <SelectTrigger className="h-11 w-full min-w-0" aria-label="Department"><SelectValue placeholder={!schoolId ? "Choose a school first" : academicOptionsLoading ? "Loading departments…" : "Choose your department"} /></SelectTrigger>
                  <SelectContent>{selectedDepartments.map((department) => <SelectItem key={department.id} value={department.id}>{department.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            {academicOptionsError ? <Alert variant="destructive" role="alert"><AlertDescription className="space-y-2"><span>We couldn’t load academic options. {academicOptionsErrorMessage || "Please try again."}</span><Button type="button" size="sm" variant="outline" onClick={() => setAcademicOptionsRetry((value) => value + 1)}>Retry loading academic options</Button></AlertDescription></Alert> : null}
            {verifiedDomainMatch && !academicOptionsLoading && !academicOptionsError && academicOptions.schools.length === 0 ? <p className="text-xs text-muted-foreground">No active schools are configured for this institution yet. Please contact your institution administrator.</p> : null}
            {role === "student" ? (
              <>
                <div className="min-w-0 space-y-2">
                  <Label>Programme / Course</Label>
                  <Select value={programmeId} onValueChange={(value) => setProgrammeId(value ?? "")} disabled={!departmentId || academicOptionsLoading || academicOptionsError || selectedProgrammes.length === 0} required>
                    <SelectTrigger className="h-11 w-full min-w-0" aria-label="Programme"><SelectValue placeholder={!departmentId ? "Choose a department first" : academicOptionsLoading ? "Loading programmes…" : "Choose your programme"} /></SelectTrigger>
                    <SelectContent>{selectedProgrammes.map((programme) => <SelectItem key={programme.id} value={programme.id}>{programme.name} · {programme.degree_level}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="min-w-0 space-y-2"><Label htmlFor="enrollment_number">Enrollment number</Label><Input id="enrollment_number" name="enrollment_number" autoComplete="off" placeholder="Student ID" maxLength={64} required /><p className="text-xs text-muted-foreground">Your institution can assign your cohort after registration.</p></div>
              </>
            ) : (
              <div className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="min-w-0 space-y-2"><Label htmlFor="employee_code">Employee code</Label><Input id="employee_code" name="employee_code" autoComplete="off" placeholder="Staff ID" maxLength={64} required /></div>
                <div className="min-w-0 space-y-2"><Label htmlFor="designation">Designation</Label><Input id="designation" name="designation" placeholder="e.g. Assistant Professor" maxLength={100} required /></div>
              </div>
            )}

            <div className="min-w-0 space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative min-w-0">
                <LockKeyhole aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={12} maxLength={128} placeholder="At least 12 characters" required aria-describedby="password-hint" className="pl-10 pr-12" />
                <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} className="absolute right-1.5 top-1/2 inline-flex size-9 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  {showPassword ? <EyeOff aria-hidden="true" className="size-4" /> : <Eye aria-hidden="true" className="size-4" />}
                </button>
              </div>
              <p id="password-hint" className="text-xs leading-5 text-muted-foreground">Use 12–128 characters.</p>
            </div>

            <div className="min-w-0 space-y-2">
              <Label htmlFor="confirm_password">Confirm password</Label>
              <div className="relative min-w-0">
                <Input id="confirm_password" name="confirm_password" type={showConfirmPassword ? "text" : "password"} autoComplete="new-password" minLength={12} maxLength={128} placeholder="Enter your password again" required aria-describedby={error ? "registration-error" : undefined} aria-invalid={Boolean(error && error.includes("password"))} className="pr-12" />
                <button type="button" onClick={() => setShowConfirmPassword((value) => !value)} aria-label={showConfirmPassword ? "Hide confirmation password" : "Show confirmation password"} aria-pressed={showConfirmPassword} className="absolute right-1.5 top-1/2 inline-flex size-9 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  {showConfirmPassword ? <EyeOff aria-hidden="true" className="size-4" /> : <Eye aria-hidden="true" className="size-4" />}
                </button>
              </div>
            </div>

            {error && <Alert id="registration-error" variant="destructive" role="alert" aria-live="polite" className="min-w-0 break-words"><AlertDescription>{error}</AlertDescription></Alert>}

            <Button type="submit" size="lg" className="h-11 w-full whitespace-normal" disabled={isSubmitting || !verifiedDomainMatch || academicOptionsLoading || academicOptionsError || !academicOptions.schools.some((school) => school.id === schoolId) || !academicOptions.departments.some((department) => department.id === departmentId && department.school_id === schoolId) || (role === "student" && !academicOptions.programmes.some((programme) => programme.id === programmeId && programme.department_id === departmentId))}>
              {isSubmitting ? "Creating your account…" : "Create account"}
              {!isSubmitting && <ArrowRight aria-hidden="true" className="ml-2 size-4" />}
            </Button>
            <p className="text-center text-xs leading-5 text-muted-foreground">
              Email verification is required. Faculty accounts also require institutional approval.
            </p>
          </form>
        </>
      )}
    </AuthFrame>
  );
};

export default BoxedRegister;
