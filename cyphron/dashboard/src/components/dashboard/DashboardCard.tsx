"use client";

import type { ReactNode } from "react";
import { MoreHorizontal } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Props = {
  title: string;
  children: ReactNode;
  className?: string;
  headerRight?: ReactNode;
  showChrome?: boolean;
};

export function DashboardCard({
  title,
  children,
  className,
  headerRight,
  showChrome = false,
}: Props) {
  return (
    <Card
      className={cn(
        "relative flex h-full min-h-0 flex-col rounded-xl border-border bg-white p-0 dark:border-white/10 dark:bg-zinc-900",
        className
      )}
    >
      {showChrome ? (
        <div className="flex shrink-0 items-center justify-center pt-3">
          <span className="text-ink-muted/25 select-none text-xs" aria-hidden>
            ···
          </span>
        </div>
      ) : null}
      <CardHeader className="flex shrink-0 flex-row items-start justify-between gap-2 space-y-0 px-5 pb-2 pt-4">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        <div className="flex items-center gap-2">
          {headerRight}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0 text-ink-muted" aria-label="Card menu">
                <MoreHorizontal className="h-4 w-4" strokeWidth={1.75} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              <DropdownMenuItem>Refresh data</DropdownMenuItem>
              <DropdownMenuItem>Export</DropdownMenuItem>
              <DropdownMenuItem>Card settings</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col px-5 pb-5 pt-0">{children}</CardContent>
    </Card>
  );
}
