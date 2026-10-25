import React from "react";
import FullLogo from "../../shared/logo/FullLogo";
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarHeader,
} from "@/components/ui/sidebar";
import { useAuth } from "@/context/auth/AuthContext";
import NavCollapse from "./nav-collapse";
import { NavUser } from "./NavUser";
import sidebarItems, { type ChildItem, type KairosRole, type MenuItem } from "./sidebaritems";

function filterItem(item: ChildItem, roles: Set<string>): ChildItem | null {
  if (item.roles && !item.roles.some((role) => roles.has(role))) return null;
  if (!item.items) return item;
  const children = item.items.map((child) => filterItem(child, roles)).filter((child): child is ChildItem => child !== null);
  return children.length ? { ...item, items: children } : null;
}

function filterMenu(menu: MenuItem[], roleNames: string[]): MenuItem[] {
  const roles = new Set(roleNames.map((role) => role.toUpperCase()));
  return menu.map((section) => ({
    ...section,
    items: section.items.map((item) => filterItem(item, roles)).filter((item): item is ChildItem => item !== null),
  })).filter((section) => section.items.length > 0);
}

const SidebarLayout = ({ ...props }: React.ComponentProps<typeof Sidebar>) => {
  const { account } = useAuth();
  const menu = filterMenu(sidebarItems, (account?.roles ?? []) as KairosRole[]);

  return (
    <Sidebar
      variant="sidebar"
      collapsible="icon"
      {...props}
      className="sidebar-box"
      side="left"
    >
      <SidebarHeader className="flex h-14 shrink-0 flex-row items-center justify-between overflow-hidden border-b border-sidebar-border/70 px-4 py-2.5 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-1">
        <div className="min-w-0 overflow-hidden"><FullLogo /></div>
      </SidebarHeader>
      <SidebarContent className="min-h-0 px-2 py-3">
        <SidebarGroup className="min-w-0 p-0 group-data-[collapsible=icon]:px-0">
          <NavCollapse menu={menu} />
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border/70 p-2">
        <NavUser />
      </SidebarFooter>
    </Sidebar>
  );
};

export default SidebarLayout;
