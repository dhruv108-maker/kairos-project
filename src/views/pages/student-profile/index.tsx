import StudentProfileBuilder from "@/components/user-profile/StudentProfileBuilder";
import AadhaarVerificationCard from "@/components/user-profile/AadhaarVerificationCard";

export default function StudentProfilePage() {
  return (
    <div className="space-y-5">
      <StudentProfileBuilder />
      <div className="mx-auto w-full max-w-[1440px] px-4 pb-8 sm:px-6 lg:px-8">
        <AadhaarVerificationCard />
      </div>
    </div>
  );
}
