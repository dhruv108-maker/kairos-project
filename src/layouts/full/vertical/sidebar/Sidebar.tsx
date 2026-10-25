import React from "react";
import SimpleBar from "simplebar-react";
import FullLogo from "../../shared/logo/FullLogo";
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarHeader, SidebarSeparator,
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
      variant="inset"
      collapsible="icon"
      {...props}
      className="sidebar-box **:data-[slot=sidebar-inner]:bg-sidebar **:data-[slot=sidebar-inner]:border **:data-[slot=sidebar-inner]:border-sidebar-border"
      side="left"
    >
      <SidebarHeader className="flex flex-row items-center justify-between border-b border-sidebar-border p-3 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-2">
        <FullLogo />
      </SidebarHeader>
      <SidebarContent className="px-2 py-3">
        <SimpleBar style={{ height: "100%" }}>
          <SidebarGroup className="p-0">
            <NavCollapse menu={menu} />
          </SidebarGroup>
        </SimpleBar>
      </SidebarContent>
      <SidebarSeparator />
      <SidebarFooter className="p-2">
        <NavUser />
      </SidebarFooter>
    </Sidebar>
  );
};

export default SidebarLayout;
