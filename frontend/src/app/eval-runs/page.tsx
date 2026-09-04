"use client";
import { useQuery } from "@tanstack/react-query";
import { evalRunsApi } from "@/lib/api";
import Link from "next/link";
import { Plus, Play } from "lucide-react";
import { clsx } from "clsx";

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    completed: "bg-emerald-900/40 text-emerald-300",
    running:   "bg-blue-900/40 text-blue-300 animate-pulse",
    queued:    "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400",
    failed:    "bg-red-900/40 text-red-300",
    cancelled: "bg-gray-100 dark:bg-gray-800 text-gray-500",
  };
  return (
    <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium", map[status] ?? "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400")}>
      {status}
    </span>
  );
}

export default function EvalRunsPage() {
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["eval-runs-list"],
    queryFn: () => evalRunsApi.list({ limit: 50 }),
    refetchOnMount: "always",
    staleTime: 0,
    refetchInterval: 5000,
  });

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Eval Runs</h1>
          <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">All evaluation runs for this workspace</p>
        </div>
        <Link
          href="/eval-runs/new"
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} /> New Eval Run
        </Link>
      </div>

      {isLoading ? (
        <div className="text-gray-500 dark:text-gray-600 text-sm">Loading...</div>
      ) : runs.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-12 text-center">
          <Play size={32} className="text-gray-400 dark:text-gray-700 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No eval runs yet.</p>
          <Link href="/eval-runs/new" className="text-indigo-400 text-sm hover:underline mt-1 inline-block">
            Create your first eval run →
          </Link>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 divide-y divide-gray-200 dark:divide-gray-800">
          {runs.map((run: any) => (
            <Link
              key={run.id}
              href={`/eval-runs/${run.id}`}
              className="flex items-center justify-between px-6 py-4 hover:bg-gray-100 dark:hover:bg-gray-800/40 transition-colors"
            >
              <div>
                <div className="text-sm text-white font-mono">{run.id.slice(0, 8)}...</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {run.eval_types?.join(" · ")} · {run.total_rows} rows · {run.completed_rows}/{run.total_rows} done
                </div>
              </div>
              <div className="flex items-center gap-4">
                {run.overall_score !== null && run.overall_score !== undefined && (
                  <div className={clsx(
                    "text-sm font-bold tabular-nums",
                    run.overall_score >= 80 ? "text-emerald-400" :
                    run.overall_score >= 60 ? "text-yellow-400" : "text-red-400"
                  )}>
                    {run.overall_score.toFixed(1)}
                  </div>
                )}
                <StatusBadge status={run.status} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
