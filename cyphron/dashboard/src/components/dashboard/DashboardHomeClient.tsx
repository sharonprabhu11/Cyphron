"use client";

import { AlertTicker } from "@/components/dashboard/AlertTicker";
import { FraudDonutCard } from "@/components/dashboard/FraudDonutCard";
import { LiveTransactionsChart } from "@/components/dashboard/LiveTransactionsChart";
import { RiskVolumeComboCard } from "@/components/dashboard/RiskVolumeComboCard";
import { SummaryStrip } from "@/components/dashboard/SummaryStrip";
import { TransactionCategoryTable } from "@/components/dashboard/TransactionCategoryTable";
import {
  mockCategoryRows,
  mockFraudSignals,
  mockRiskVolume,
  mockSummaryKpis,
} from "@/lib/dashboard/mockData";

export function DashboardHomeClient() {
  return (
    <div className="mx-auto flex max-w-[1600px] flex-col gap-6">
      <div className="grid grid-cols-1 items-stretch gap-6 lg:grid-cols-12">
        <div className="flex min-h-0 min-w-0 lg:col-span-3">
          <SummaryStrip items={mockSummaryKpis} />
        </div>
        <div className="flex min-h-0 min-w-0 lg:col-span-4">
          <FraudDonutCard data={mockFraudSignals} />
        </div>
        <div className="flex min-h-0 min-w-0 lg:col-span-5">
          <TransactionCategoryTable rows={mockCategoryRows} />
        </div>
      </div>

      <AlertTicker />

      <div className="grid grid-cols-1 items-stretch gap-6 xl:grid-cols-2 xl:auto-rows-[1fr]">
        <div className="flex min-h-[min(24rem,50vh)] min-w-0 xl:min-h-[20rem]">
          <LiveTransactionsChart />
        </div>
        <div className="flex min-h-[min(24rem,50vh)] min-w-0 xl:min-h-[20rem]">
          <RiskVolumeComboCard data={mockRiskVolume} />
        </div>
      </div>
    </div>
  );
}
