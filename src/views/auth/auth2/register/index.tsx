import { Card } from "@/components/ui/card";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import FullLogo from "src/layouts/full/shared/logo/FullLogo";

const BoxedRegister = () => (
  <div className="flex min-h-screen items-center justify-center bg-muted px-4 py-10">
    <Card className="w-full max-w-md border-none p-6 shadow-lg">
      <div className="mx-auto mb-6 w-fit"><FullLogo /></div>
      <h1 className="text-center text-2xl font-semibold tracking-tight">Join Kairos</h1>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">
        Student and faculty accounts are linked to institution-specific academic records.
        To protect those records, registration must use the onboarding details provided by
        your institution rather than a generic sign-up form.
      </p>
      <p className="mt-4 text-sm text-muted-foreground">
        Contact your institution administrator for the correct student or faculty registration
        process. Faculty accounts also require institutional approval.
      </p>
      <Button asChild className="mt-6 w-full rounded-lg">
        <Link to="/auth/auth2/login">Back to sign in</Link>
      </Button>
    </Card>
  </div>
);

export default BoxedRegister;
