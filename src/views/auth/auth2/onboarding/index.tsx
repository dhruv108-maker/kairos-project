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
      footer={
        <>
          Already have an account?{" "}
          <button
            type="button"
            onClick={() => navigate("/auth/auth2/login")}
            className="rounded-sm font-medium text-foreground underline decoration-border underline-offset-4 transition-colors hover:decoration-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            Sign in
          </button>
        </>
      }
    >
      <section className="mx-auto w-full min-w-0" aria-labelledby="onboarding-title">
        <header className="mb-7 min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Account setup
          </p>
          <h1
            id="onboarding-title"
            className="mt-2 break-words text-3xl font-semibold leading-tight tracking-[-0.035em] text-foreground sm:text-[2rem]"
          >
            How will you use Kairos?
          </h1>
          <p className="mt-3 max-w-prose text-sm leading-6 text-muted-foreground">
            Choose the role that matches your institution record. You’ll provide the corresponding academic details next.
          </p>
        </header>

        <div className="grid min-w-0 grid-cols-1 gap-3">
          <Card className="min-w-0 gap-0 rounded-lg border border-border bg-card py-0 shadow-none transition-colors duration-150 hover:border-foreground/30">
            <CardHeader className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-3 gap-y-0 px-4 pt-4 pb-3 sm:px-5 sm:pt-5">
              <div className="row-span-2 flex size-10 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-foreground">
                <GraduationCap aria-hidden="true" className="size-5" />
              </div>
              <CardTitle className="min-w-0 pt-0.5 text-base font-semibold tracking-tight">
                I’m a student
              </CardTitle>
              <CardDescription className="min-w-0 leading-5">
                Join your cohort using your enrollment number and cohort ID.
              </CardDescription>
            </CardHeader>
            <CardContent className="px-4 pb-4 sm:px-5 sm:pb-5">
              <Button
                className="h-10 w-full justify-between gap-3"
                onClick={() => navigate("/auth/auth2/register?role=student")}
              >
                <span>Continue as student</span>
                <ArrowRight aria-hidden="true" className="size-4" />
              </Button>
            </CardContent>
          </Card>

          <Card className="min-w-0 gap-0 rounded-lg border border-border bg-card py-0 shadow-none transition-colors duration-150 hover:border-foreground/30">
            <CardHeader className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-3 gap-y-0 px-4 pt-4 pb-3 sm:px-5 sm:pt-5">
              <div className="row-span-2 flex size-10 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-foreground">
                <UsersRound aria-hidden="true" className="size-5" />
              </div>
              <CardTitle className="min-w-0 pt-0.5 text-base font-semibold tracking-tight">
                I’m faculty
              </CardTitle>
              <CardDescription className="min-w-0 leading-5">
                Connect your employee code and department. Faculty access remains pending until institution approval.
              </CardDescription>
            </CardHeader>
            <CardContent className="px-4 pb-4 sm:px-5 sm:pb-5">
              <Button
                variant="outline"
                className="h-10 w-full justify-between gap-3"
                onClick={() => navigate("/auth/auth2/register?role=faculty")}
              >
                <span>Continue as faculty</span>
                <ArrowRight aria-hidden="true" className="size-4" />
              </Button>
            </CardContent>
          </Card>
        </div>

        <aside className="mt-5 flex min-w-0 items-start gap-3 rounded-lg border border-border bg-muted/30 p-3.5 sm:p-4">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-background text-muted-foreground">
            <ShieldCheck aria-hidden="true" className="size-4" />
          </div>
          <p className="min-w-0 break-words pt-0.5 text-xs leading-5 text-muted-foreground">
            <span className="font-medium text-foreground">Need administrator access?</span>{" "}
            Institute administrator access is managed through institutional setup and authorization, not public self-registration. Contact your institution for assistance.
          </p>
        </aside>

        <p className="mt-4 break-words text-xs leading-5 text-muted-foreground">
          You’ll need the cohort or department details supplied by your institution and access to your email for verification.
        </p>
      </section>
    </AuthFrame>
  );
};

export default Onboarding;
