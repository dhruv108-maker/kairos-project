import {
  Activity, BookOpen, Bookmark, BriefcaseBusiness, ClipboardList, FileText, House,
  LayoutDashboard, NotebookTabs, Settings, Settings2, ShieldCheck, Ticket, UserRound, Users, GraduationCap,
  type LucideIcon,
} from "lucide-react";

export type KairosRole =
  | "STUDENT" | "FACULTY" | "INDUSTRY_MENTOR" | "EMPLOYER"
  | "RECRUITER" | "EMPLOYER_ADMIN" | "INSTITUTION_ADMIN" | "ADMIN"
  | "PLATFORM_ADMIN";

export interface ChildItem {
  id: string;
  name: string;
  icon?: LucideIcon;
  items?: ChildItem[];
  url?: string;
  roles?: KairosRole[];
  disabled?: boolean;
  external?: boolean;
  color?: string;
  badge?: boolean;
  badgeType?: "filled" | "outlined";
  badgeContent?: string;
  isPro?: boolean;
}

export interface MenuItem {
  heading: string;
  items: ChildItem[];
}

const recruiterRoles: KairosRole[] = ["EMPLOYER", "RECRUITER", "EMPLOYER_ADMIN", "ADMIN"];
const studentRoles: KairosRole[] = ["STUDENT"];
const internshipRoles: KairosRole[] = ["STUDENT", "FACULTY", "INDUSTRY_MENTOR", "INSTITUTION_ADMIN", "ADMIN"];

const sidebarItems: MenuItem[] = [
  {
    heading: "Workspace",
    items: [
      { id: "overview", name: "Overview", icon: House, url: "/" },
    ],
  },
  {
    heading: "Institution",
    items: [
      { id: "institution-dashboard", name: "Institution Dashboard", icon: GraduationCap, roles: ["INSTITUTION_ADMIN"], url: "/institution/dashboard" },
    ],
  },
  {
    heading: "Faculty",
    items: [
      { id: "faculty-progress", name: "Student Progress", icon: Users, roles: ["FACULTY"], url: "/faculty/progress" },
    ],
  },
  {
    heading: "Internships",
    items: [
      { id: "internship-workspace", name: "Internship Workspace", icon: BriefcaseBusiness, roles: internshipRoles, items: [
        { id: "internship-active", name: "My Internship & Work Logs", icon: Activity, url: "/internships/during", roles: internshipRoles },
      ] },
    ],
  },
  {
    heading: "Recruitment",
    items: [
      { id: "jobs-hub", name: "Jobs Hub", icon: BriefcaseBusiness, items: [
        { id: "job-discovery", name: "Discover Jobs", icon: BriefcaseBusiness, url: "/jobs" },
        { id: "my-applications", name: "My Applications", icon: FileText, url: "/jobs/applications", roles: studentRoles },
        { id: "saved-jobs", name: "Saved Jobs", icon: Bookmark, url: "/jobs/saved", roles: studentRoles },
        { id: "campus-recruitment", name: "Campus Recruitment", icon: Users, url: "/jobs/campus", roles: studentRoles },
      ] },
      { id: "recruiter-management", name: "Recruitment Management", icon: ClipboardList, roles: recruiterRoles, items: [
        { id: "recruiter-listings", name: "My Listings", icon: BriefcaseBusiness, url: "/jobs/recruiter", roles: recruiterRoles },
        { id: "recruiter-create", name: "Create Listing", icon: FileText, url: "/jobs/recruiter/create", roles: recruiterRoles },
        { id: "recruiter-applications", name: "Applications Pipeline", icon: Users, url: "/jobs/recruiter/applications", roles: recruiterRoles },
      ] },
    ],
  },
  {
    heading: "Account",
    items: [
      { id: "account-profile", name: "My Profile", icon: UserRound, url: "/pages/user-profile" },
      { id: "settings", name: "Settings", icon: Settings, url: "/settings" },
      { id: "student-profile", name: "Student Profile", icon: NotebookTabs, url: "/student/profile", roles: studentRoles },
      { id: "aadhaar-verification", name: "Aadhaar Verification", icon: ShieldCheck, url: "/student/profile", roles: studentRoles },
    ],
  },
  {
    heading: "Workspace Tools",
    items: [
      { id: "notes", name: "Notes", icon: BookOpen, url: "/apps/notes" },
      { id: "support-tickets", name: "Support Tickets", icon: Ticket, url: "/apps/tickets" },
      { id: "blog", name: "Blog", icon: FileText, items: [
        { id: "blog-posts", name: "Browse Posts", icon: BookOpen, url: "/apps/blog/post" },
        { id: "blog-manage", name: "Manage Posts", icon: Settings2, url: "/apps/blog/manage-blog", roles: ["FACULTY", "ADMIN", "INSTITUTION_ADMIN"] },
      ] },
      { id: "academic-data", name: "Academic Data", icon: LayoutDashboard, items: [
        { id: "data-tables", name: "Data Tables", icon: ClipboardList, url: "/pages/tables" },
        { id: "forms", name: "Forms", icon: FileText, url: "/pages/form" },
      ] },
    ],
  },
];

export default sidebarItems;
