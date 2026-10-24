import { useNavigate } from "react-router";
import { ArrowRight, GraduationCap, ShieldCheck, UsersRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import AuthFrame from "@/components/auth/AuthFrame";

const Onboarding = () => {
  const navigate = useNavigate();

  return (
    <AuthFrame
      asideEyebrow="Get started"
      asideTitle="Start with the right access for your academic role."
      asideDescription="Kairos connects students and faculty to the academic communities they belong to, with verification and institutional approval built into the process."
      footer={<>Already have an account? <button type="button" onClick={() => navigate("/auth/auth2/login")} className="font-medium text-foreground underline underline-offset-4 hover:text-muted-foreground">Sign in</button></>}
    >
      <div className="mb-7">
        <p className="text-sm font-medium text-muted-foreground">ACCOUNT SETUP</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">How will you use Kairos?</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">Choose the role that matches your institution record. You’ll provide the corresponding academic details next.</p>
      </div>

      <div className="space-y-3">
        <Card className="gap-0 rounded-lg border shadow-none transition-colors hover:border-foreground/30">
          <CardHeader className="pb-3">
            <div className="mb-2 flex size-10 items-center justify-center rounded-md border bg-muted">
              <GraduationCap className="size-5" />
            </div>
            <CardTitle className="text-base">I’m a student</CardTitle>
            <CardDescription className="leading-5">Join your cohort using your enrollment number and cohort ID.</CardDescription>
          </CardHeader>
          <CardContent className="pb-4">
            <Button className="w-full" onClick={() => navigate("/auth/auth2/register?role=student")}>
              Continue as student <ArrowRight className="ml-2 size-4" />
            </Button>
          </CardContent>
        </Card>

        <Card className="gap-0 rounded-lg border shadow-none transition-colors hover:border-foreground/30">
          <CardHeader className="pb-3">
            <div className="mb-2 flex size-10 items-center justify-center rounded-md border bg-muted">
              <UsersRound className="size-5" />
            </div>
            <CardTitle className="text-base">I’m faculty</CardTitle>
            <CardDescription className="leading-5">Connect your employee code and department. Faculty access remains pending until institution approval.</CardDescription>
          </CardHeader>
          <CardContent className="pb-4">
            <Button variant="outline" className="w-full" onClick={() => navigate("/auth/auth2/register?role=faculty")}>
              Continue as faculty <ArrowRight className="ml-2 size-4" />
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="mt-5 flex items-start gap-3 rounded-lg border bg-muted/40 p-4">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        <p className="text-xs leading-5 text-muted-foreground">
          Institute administrator access is managed through institutional setup and authorization, not public self-registration. If you need administrator access, contact your institution.
        </p>
      </div>
      <p className="mt-5 text-xs leading-5 text-muted-foreground">You’ll need the cohort or department details supplied by your institution and access to your email for verification.</p>
    </AuthFrame>
  );
};

export default Onboarding;
