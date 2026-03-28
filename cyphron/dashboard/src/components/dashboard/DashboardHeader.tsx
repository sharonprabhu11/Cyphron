"use client";

import { useEffect, useState } from "react";
import { Bell, CalendarRange, Moon, Sun, UserRound } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const iconBtn =
  "h-10 w-10 rounded-xl border-0 bg-transparent text-ink-muted hover:bg-surface-muted hover:text-primary dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-primary";

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" className={cn(iconBtn)} disabled aria-hidden>
        <Moon className="h-5 w-5 opacity-0" />
      </Button>
    );
  }

  const dark = resolvedTheme === "dark";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={iconBtn}
          aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
          onClick={() => setTheme(dark ? "light" : "dark")}
        >
          {dark ? <Sun className="h-5 w-5 text-amber-400" strokeWidth={1.75} /> : <Moon className="h-5 w-5" strokeWidth={1.75} />}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="bottom" sideOffset={8}>
        {dark ? "Light mode" : "Dark mode"}
      </TooltipContent>
    </Tooltip>
  );
}

export function DashboardHeader() {
  const range = "Last 30 days";
  const today = new Date().toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  return (
    <header className="flex shrink-0 items-center justify-between gap-4 border-b border-border bg-white px-6 py-4 lg:px-8 dark:border-white/10 dark:bg-zinc-900">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">Dashboard</h1>
        <p className="mt-0.5 text-sm text-ink-muted">Cyphron fraud operations overview</p>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-2 rounded-pill border border-border bg-muted px-4 py-2 text-sm text-ink-muted dark:border-white/10 dark:bg-zinc-800/80 sm:flex">
          <CalendarRange className="h-4 w-4 text-primary" strokeWidth={1.75} />
          <span className="font-medium text-ink">{range}</span>
          <span className="text-ink-muted/70">· {today}</span>
        </div>
        <ThemeToggle />
        <Button variant="ghost" size="icon" className={iconBtn} aria-label="Notifications">
          <Bell className="h-5 w-5" strokeWidth={1.75} />
        </Button>
        <Button variant="ghost" size="icon" className={cn(iconBtn, "text-primary hover:text-primary")} aria-label="Account">
          <UserRound className="h-5 w-5" strokeWidth={1.75} />
        </Button>
      </div>
    </header>
  );
}
