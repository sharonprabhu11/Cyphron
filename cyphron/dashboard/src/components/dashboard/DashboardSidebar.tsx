"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bell,
  FileText,
  GitBranch,
  LayoutDashboard,
  ListTodo,
  Settings,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard },
  { href: "/dashboard/alerts", label: "Alerts", icon: Bell },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/dashboard/review-queue", label: "Review queue", icon: ListTodo },
  { href: "/dashboard/live-graph", label: "Live graph", icon: GitBranch },
  { href: "/dashboard/str-viewer", label: "STR viewer", icon: FileText },
];

export function DashboardSidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-[72px] shrink-0 flex-col items-center border-r border-border bg-white py-6 dark:border-white/10 dark:bg-zinc-900">
      <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-sm font-bold text-primary-foreground">
        C
      </div>
      <nav className="flex flex-1 flex-col gap-2">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Tooltip key={href}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-11 w-11 rounded-xl text-ink-muted hover:bg-surface-muted hover:text-primary dark:hover:bg-zinc-800 dark:hover:text-primary",
                    active && "bg-brand-blue-muted/80 text-primary dark:bg-primary/20"
                  )}
                  asChild
                >
                  <Link href={href} aria-label={label}>
                    <Icon className="h-5 w-5" strokeWidth={1.75} />
                  </Link>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right" sideOffset={8}>
                {label}
              </TooltipContent>
            </Tooltip>
          );
        })}
      </nav>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="mt-auto h-11 w-11 rounded-xl text-ink-muted hover:bg-surface-muted hover:text-primary dark:hover:bg-zinc-800"
            aria-label="Settings"
            asChild
          >
            <Link href="#">
              <Settings className="h-5 w-5" strokeWidth={1.75} />
            </Link>
          </Button>
        </TooltipTrigger>
        <TooltipContent side="right" sideOffset={8}>
          Settings
        </TooltipContent>
      </Tooltip>
    </aside>
  );
}
