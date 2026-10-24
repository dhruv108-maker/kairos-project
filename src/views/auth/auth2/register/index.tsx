import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import FullLogo from "src/layouts/full/shared/logo/FullLogo";
import { apiRequest } from "@/api/kairos-client";

type RegistrationRole = "student" | "faculty";

interface RegistrationResponse {
  account_id: string;
  message: string;
  verification_email_sent: boolean;
  activation_pending: boolean;
}

const BoxedRegister = () => {
  const [role, setRole] = useState<RegistrationRole>("student");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    setError("");
    setMessage("");
    setIsSubmitting(true);
    const form = new FormData(event.currentTarget);
    const common = {
      email: String(form.get("email") ?? "").trim().toLowerCase(),
      password: String(form.get("password") ?? ""),
      full_name: String(form.get("full_name") ?? "").trim(),
    };
    const payload = role === "student"
      ? {
          ...common,
          enrollment_number: String(form.get("enrollment_number") ?? "").trim(),
          cohort_id: String(form.get("cohort_id") ?? "").trim(),
        }
      : {
          ...common,
          employee_code: String(form.get("employee_code") ?? "").trim(),
          department_id: String(form.get("department_id") ?? "").trim(),
          designation: String(form.get("designation") ?? "").trim(),
        };

    try {
      const result = await apiRequest<RegistrationResponse>(`/auth/register/${role}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setMessage(result.message);
      formElement.reset();
      setRole("student");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please check your details and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted px-4 py-10">
      <Card className="w-full max-w-lg border-none p-6 shadow-lg sm:p-8">
        <div className="mx-auto mb-6 w-fit"><FullLogo /></div>
        <h1 className="text-center text-2xl font-semibold tracking-tight">Create your Kairos account</h1>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          Use the student or faculty details supplied by your institution.
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-1.5">
            <Label htmlFor="role">Account type</Label>
            <select
              id="role"
              value={role}
              onChange={(event) => setRole(event.target.value as RegistrationRole)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="student">Student</option>
              <option value="faculty">Faculty</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="full_name">Full name</Label>
            <Input id="full_name" name="full_name" autoComplete="name" maxLength={255} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input id="email" name="email" type="email" autoComplete="email" maxLength={255} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <Input id="password" name="password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required />
            <p className="text-xs text-muted-foreground">Use at least 12 characters.</p>
          </div>

          {role === "student" ? (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="enrollment_number">Enrollment number</Label>
                <Input id="enrollment_number" name="enrollment_number" maxLength={64} required />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="cohort_id">Cohort ID</Label>
                <Input id="cohort_id" name="cohort_id" maxLength={36} required />
              </div>
            </>
          ) : (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="employee_code">Employee code</Label>
                <Input id="employee_code" name="employee_code" maxLength={64} required />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="department_id">Department ID</Label>
                <Input id="department_id" name="department_id" maxLength={36} required />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="designation">Designation</Label>
                <Input id="designation" name="designation" maxLength={100} required />
              </div>
              <p className="text-xs text-muted-foreground">
                Faculty accounts remain inactive until institutional approval.
              </p>
            </>
          )}

          {message && <p role="status" className="rounded-md border border-border p-3 text-sm">{message}</p>}
          {error && <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</p>}

          <Button type="submit" className="w-full rounded-lg" disabled={isSubmitting}>
            {isSubmitting ? "Creating account…" : "Create account"}
          </Button>
        </form>

        <p className="mt-5 text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link className="font-medium text-primary hover:underline" to="/auth/auth2/login">Sign in</Link>
        </p>
      </Card>
    </div>
  );
};

export default BoxedRegister;
