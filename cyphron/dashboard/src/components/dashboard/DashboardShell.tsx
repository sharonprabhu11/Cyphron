"use client";

import type { ReactNode } from "react";

import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { DashboardSidebar } from "@/components/dashboard/DashboardSidebar";
import { TooltipProvider } from "@/components/ui/tooltip";

export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex min-h-screen bg-surface-muted dark:bg-background">
        <DashboardSidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <DashboardHeader />
          <div className="flex-1 overflow-auto bg-surface p-6 lg:p-8 dark:bg-background">{children}</div>
        </div>
      </div>
    </TooltipProvider>
  );
}
