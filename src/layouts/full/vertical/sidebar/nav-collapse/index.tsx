import { useEffect, useState } from "react";
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
    return rest.length > 0 && !rest.slice(1).includes("/") && !["/applications", "/saved", "/campus", "/recruiter"].includes(rest);
  }
  return pathname.startsWith(url.endsWith("/") ? url : `${url}/`);
}

function hasActiveDescendant(item: ChildItem, pathname: string): boolean {
  return routeMatches(pathname, item.url) || Boolean(item.items?.some((child) => hasActiveDescendant(child, pathname)));
}

function NavEntry({ item, pathname, depth = 0 }: { item: ChildItem; pathname: string; depth?: number }) {
  const { isMobile, setOpenMobile } = useSidebar();
  const hasChildren = Boolean(item.items?.length);
  const active = hasActiveDescendant(item, pathname);
  const [manualOpen, setManualOpen] = useState<boolean | null>(null);
  const open = manualOpen ?? active;
  const Icon = item.icon as LucideIcon | undefined;
  const onNavigate = () => { if (isMobile) setOpenMobile(false); };

  useEffect(() => {
    setManualOpen(null);
  }, [pathname]);

  if (hasChildren) {
    return (
      <SidebarMenuItem>
        <Collapsible open={open} onOpenChange={setManualOpen} className="group/collapsible">
          <CollapsibleTrigger
            render={
              <SidebarMenuButton
                isActive={active && !item.items?.some((child) => hasActiveDescendant(child, pathname))}
                tooltip={item.name}
                aria-expanded={open}
              >
                {Icon ? <Icon aria-hidden="true" /> : null}
                <span className="min-w-0 flex-1 truncate group-data-[collapsible=icon]:hidden">{item.name}</span>
                <ChevronDown aria-hidden="true" className="ml-auto size-4 shrink-0 transition-transform group-data-[open]/collapsible:rotate-180 group-data-[collapsible=icon]:hidden" />
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
  const childActive = routeMatches(pathname, item.url);

  if (depth > 0) {
    return (
      <SidebarMenuSubItem>
        <SidebarMenuSubButton
          render={<Link to={item.url} onClick={onNavigate} aria-current={childActive ? "page" : undefined} />}
          isActive={childActive}
          className={item.disabled ? "pointer-events-none opacity-50" : undefined}
          aria-disabled={item.disabled || undefined}
          tabIndex={item.disabled ? -1 : undefined}
        >
          {Icon ? <Icon aria-hidden="true" /> : null}
          <span className="truncate">{item.name}</span>
        </SidebarMenuSubButton>
      </SidebarMenuSubItem>
    );
  }

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        render={<Link to={item.url} onClick={onNavigate} aria-current={childActive ? "page" : undefined} />}
        isActive={routeMatches(pathname, item.url)}
        tooltip={item.name}
        className={item.disabled ? "pointer-events-none opacity-50" : undefined}
        aria-disabled={item.disabled || undefined}
        tabIndex={item.disabled ? -1 : undefined}
      >
        {Icon ? <Icon aria-hidden="true" /> : null}
        <span className="min-w-0 flex-1 truncate group-data-[collapsible=icon]:hidden">{item.name}</span>
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
            <SidebarGroupLabel>
              {section.heading}
            </SidebarGroupLabel>
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
