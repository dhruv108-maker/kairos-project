import { uniqueId } from "lodash";
import { BriefcaseBusiness, House, UserRound, type LucideIcon } from "lucide-react";

export interface ChildItem {
  id?: number | string;
  name: string;
  icon?: LucideIcon;
  items?: ChildItem[];
  item?: unknown;
  url?: string;
  color?: string;
  disabled?: boolean;
  subtitle?: string;
  badge?: boolean;
  badgeType?: string;
  badgeContent?: string;
  isActive?: boolean;
  external?: boolean;
  isPro?: boolean;
}

export interface MenuItem {
  heading?: string;
  name?: string;
  icon?: LucideIcon;
  id?: number;
  to?: string;
  item?: MenuItem[];
  items?: ChildItem[];
  url?: string;
  disabled?: boolean;
  subtitle?: string;
  badgeType?: string;
  badge?: boolean;
  badgeContent?: string;
  isActive?: boolean;
  isPro?: boolean;
}

const SidebarContent: MenuItem[] = [
  {
    heading: "Workspace",
    items: [
      { id: uniqueId(), name: "Overview", icon: House, url: "/" },
      { id: uniqueId(), name: "Jobs & Internships", icon: BriefcaseBusiness, url: "/jobs" },
      { id: uniqueId(), name: "My Profile", icon: UserRound, url: "/pages/user-profile" },
      { id: uniqueId(), name: "Student Profile", icon: UserRound, url: "/student/profile" },
    ],
  },
];

export default SidebarContent;
