"use client";

import Link from "next/link";
import { ArrowLeft, Download, Printer } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { AlertRecord, AlertStrReportPayload } from "@/lib/dashboard/types";

function tierPill(tier: AlertStrReportPayload["riskTier"]) {
  const critical = tier === "CRITICAL";
  const className = critical
    ? "inline-flex rounded-md px-2.5 py-0.5 text-xs font-semibold bg-orange-600 text-white dark:bg-orange-600"
    : "inline-flex rounded-md px-2.5 py-0.5 text-xs font-semibold border border-stone-200 bg-stone-100 text-stone-700 dark:border-white/10 dark:bg-zinc-800 dark:text-zinc-200";
  return <span className={className}>{tier}</span>;
}

export function AlertReportClient({
  alert,
  report,
}: {
  alert: AlertRecord;
  report: AlertStrReportPayload;
}) {
  const hasStr = report.strReport != null && report.riskTier === "CRITICAL";
  const summaryEntries = Object.entries(report.transactionSummary);
  const pdfHref =
    report.pdfDownloadPath && report.alertId
      ? `/api/alerts/${encodeURIComponent(report.alertId)}/report/pdf`
      : report.pdfDownloadPath;

  return (
    <div className="str-report-print-root space-y-5 print:space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Button variant="ghost" size="sm" className="-ml-2 gap-1 text-stone-600 dark:text-zinc-400" asChild>
          <Link href="/dashboard/alerts">
            <ArrowLeft className="h-4 w-4" />
            Back to alerts
          </Link>
        </Button>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="rounded-lg border-stone-200 dark:border-white/10"
            onClick={() => window.print()}
          >
            <Printer className="h-4 w-4" />
            Print
          </Button>
          {pdfHref ? (
            <Button size="sm" className="rounded-lg bg-orange-500 hover:bg-orange-600 dark:bg-orange-600" asChild>
              <a href={pdfHref} download>
                <Download className="h-4 w-4" />
                Download PDF
              </a>
            </Button>
          ) : null}
        </div>
      </div>

      <Card className="rounded-xl border-stone-200/90 bg-white shadow-none print:border-0 print:shadow-none dark:border-white/10 dark:bg-zinc-900">
        <CardHeader className="border-b border-stone-100 pb-4 dark:border-white/10">
          <CardDescription className="text-xs text-stone-500 dark:text-zinc-400">Suspicious Transaction Report</CardDescription>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="text-xl text-stone-900 dark:text-zinc-50">{alert.alertId}</CardTitle>
            {tierPill(report.riskTier)}
          </div>
          <div className="mt-2 grid gap-1 text-sm text-stone-600 dark:text-zinc-300">
            <p>
              <span className="text-stone-500 dark:text-zinc-500">Entity</span>{" "}
              <span className="font-mono font-medium text-stone-900 dark:text-zinc-100">{report.entityId}</span>
            </p>
            <p>
              <span className="text-stone-500 dark:text-zinc-500">Risk score</span>{" "}
              <span className="tabular-nums font-semibold">{(report.riskScore * 100).toFixed(1)}%</span>
              <span className="text-stone-400 dark:text-zinc-500"> ({report.riskScore.toFixed(4)} composite)</span>
            </p>
            {report.generatedAt ? (
              <p className="text-xs text-stone-500 dark:text-zinc-400">
                Generated <time dateTime={report.generatedAt}>{new Date(report.generatedAt).toLocaleString("en-GB")}</time>
              </p>
            ) : null}
          </div>
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          <section>
            <h2 className="text-sm font-semibold text-stone-900 dark:text-zinc-100">Key risk factors</h2>
            {report.reasons.length === 0 ? (
              <p className="mt-2 text-sm text-stone-500 dark:text-zinc-400">No rule reasons listed.</p>
            ) : (
              <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-stone-700 dark:text-zinc-300">
                {report.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h2 className="text-sm font-semibold text-stone-900 dark:text-zinc-100">Transaction summary</h2>
            <div className="mt-3 overflow-x-auto rounded-lg border border-stone-200 dark:border-white/10">
              <table className="w-full min-w-[280px] text-left text-sm">
                <tbody>
                  {summaryEntries.map(([key, value]) => (
                    <tr key={key} className="border-b border-stone-100 last:border-0 dark:border-white/10">
                      <th className="whitespace-nowrap bg-stone-50/80 px-3 py-2 font-medium text-stone-600 dark:bg-zinc-800/50 dark:text-zinc-400">
                        {key.replace(/_/g, " ")}
                      </th>
                      <td className="px-3 py-2 font-mono text-xs text-stone-900 dark:text-zinc-100">{value || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-stone-900 dark:text-zinc-100">Investigation summary</h2>
            {!hasStr ? (
              <div className="mt-3 rounded-lg border border-dashed border-stone-200 bg-stone-50/50 p-4 text-sm text-stone-600 dark:border-white/10 dark:bg-zinc-800/30 dark:text-zinc-400">
                <p>
                  STR narrative and PDF download are only produced when the decision pipeline marks the case as{" "}
                  <strong className="text-stone-800 dark:text-zinc-200">CRITICAL</strong> (see{" "}
                  <code className="rounded bg-stone-200/80 px-1 dark:bg-zinc-700">POST /decision</code> in the Cyphron
                  API).
                </p>
                <p className="mt-2">This alert is currently <strong>{report.riskTier}</strong> in the demo dataset.</p>
              </div>
            ) : (
              <pre className="mt-3 max-h-[min(480px,50vh)] overflow-auto whitespace-pre-wrap rounded-lg border border-stone-200 bg-stone-50/80 p-4 font-sans text-sm leading-relaxed text-stone-800 dark:border-white/10 dark:bg-zinc-950 dark:text-zinc-200">
                {report.strReport}
              </pre>
            )}
          </section>

          <p className="text-center text-xs italic text-stone-500 dark:text-zinc-500 print:mt-4">
            This report is auto-generated by Cyphron AI Detection System.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
