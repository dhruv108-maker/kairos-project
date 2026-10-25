import { useState } from "react";
import { Link, useLocation } from "react-router";
import { ChevronDown, type LucideIcon } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  SidebarGroupLabel, SidebarMenu, SidebarMenuButton, SidebarMenuItem,
  SidebarMenuSub, SidebarMenuSubButton, SidebarMenuSubItem, useSidebar,
} from "@/components/ui/sidebar";
import type { ChildItem, MenuItem } from "../sidebaritems";

interface NavCollapseProps {
  menu: MenuItem[];
  className?: string;
}

function routeMatches(pathname: string, url?: string) {
  if (!url) return false;
  if (pathname === url) return true;
  if (url === "/jobs") {
    const rest = pathname.slice("/jobs".length);
    return rest.length > 0 && !rest.slice(1).includes("/") && !["/applications", "/campus", "/recruiter"].includes(rest);
  }
  return pathname.startsWith(url.endsWith("/") ? url : `${url}/`);
}

function hasActiveDescendant(item: ChildItem, pathname: string): boolean {
  return routeMatches(pathname, item.url) || Boolean(item.items?.some((child) => hasActiveDescendant(child, pathname)));
}

function NavEntry({ item, pathname, depth = 0 }: { item: ChildItem; pathname: string; depth?: number }) {
  const { state, isMobile, setOpenMobile } = useSidebar();
  const hasChildren = Boolean(item.items?.length);
  const active = hasActiveDescendant(item, pathname);
  const [manuallyOpen, setManuallyOpen] = useState(false);
  const open = active || manuallyOpen;
  const Icon = item.icon as LucideIcon | undefined;
  const onNavigate = () => { if (isMobile) setOpenMobile(false); };

  if (hasChildren) {
    return (
      <SidebarMenuItem>
        <Collapsible open={open} onOpenChange={setManuallyOpen} className="group/collapsible">
          <CollapsibleTrigger
            render={
              <SidebarMenuButton isActive={active} tooltip={item.name} aria-expanded={open}>
                {Icon ? <Icon /> : null}
                <span>{item.name}</span>
                <ChevronDown className="ml-auto transition-transform group-data-[open]/collapsible:rotate-180" />
              </SidebarMenuButton>
            }
          />
          <CollapsibleContent>
            <SidebarMenuSub>
              {item.items!.map((child) => (
                <NavEntry key={child.id} item={child} pathname={pathname} depth={depth + 1} />
              ))}
            </SidebarMenuSub>
          </CollapsibleContent>
        </Collapsible>
      </SidebarMenuItem>
    );
  }

  if (!item.url) return null;
  if (depth > 0) {
    return (
      <SidebarMenuSubItem>
        <SidebarMenuSubButton
          render={<Link to={item.url} onClick={onNavigate} />}
          isActive={pathname === item.url || (item.url !== "/" && pathname.startsWith(`${item.url}/`))}
        >
          {Icon ? <Icon /> : null}
          <span>{item.name}</span>
        </SidebarMenuSubButton>
      </SidebarMenuSubItem>
    );
  }

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        render={<Link to={item.url} onClick={onNavigate} />}
        isActive={routeMatches(pathname, item.url)}
        tooltip={item.name}
      >
        {Icon ? <Icon /> : null}
        <span>{item.name}</span>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}

export default function NavCollapse({ menu }: NavCollapseProps) {
  const { pathname } = useLocation();
  return (
    <>
      {menu.map((section) => {
        if (!section.items.length) return null;
        return (
          <section key={section.heading} className="mb-3">
            <SidebarGroupLabel>{section.heading}</SidebarGroupLabel>
            <SidebarMenu>
              {section.items.map((item) => (
                <NavEntry key={item.id} item={item} pathname={pathname} />
              ))}
            </SidebarMenu>
          </section>
        );
      })}
    </>
  );
}
