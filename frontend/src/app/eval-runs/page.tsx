"use client";
import { useQuery } from "@tanstack/react-query";
import { evalRunsApi, type EvalRun } from "@/lib/api";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { Play, Plus, Clock } from "lucide-react";
import { clsx } from "clsx";

function scoreColor(score: number | null) {
  if (score === null) return "text-gray-600";
  if (score >= 90) return "text-emerald-400";
  if (score >= 75) return "text-green-400";
  if (score >= 60) return "text-yellow-400";
  return "text-red-400";
}

function StatusDot({ status }: { status: EvalRun["status"] }) {
  const map: Record<string, string> = {
    queued: "bg-gray-500", running: "bg-blue-400 animate-pulse",
    completed: "bg-emerald-400", failed: "bg-red-400", cancelled: "bg-gray-600",
  };
  return <span className={clsx("inline-block w-2 h-2 rounded-full mr-2", map[status] ?? "bg-gray-500")} />;
}

export default function EvalRunsPage() {
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["eval-runs"],
    queryFn: () => evalRunsApi.list({ limit: 50 }),
    refetchInterval: 5000,
  });

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Eval Runs</h1>
          <p className="text-gray-400 text-sm mt-1">All evaluation runs across your workspace</p>
        </div>
        <Link
          href="/eval-runs/new"
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          <Plus size={16} /> New Run
        </Link>
      </div>

      {isLoading ? (
        <div className="text-gray-600 text-sm">Loading...</div>
      ) : runs.length === 0 ? (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-14 text-center">
          <Play size={32} className="text-gray-700 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No eval runs yet.</p>
          <Link href="/eval-runs/new" className="text-indigo-400 text-sm hover:underline mt-1 inline-block">
            Launch your first eval →
          </Link>
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="px-5 py-3 text-left text-xs text-gray-600 uppercase tracking-wider">Run ID</th>
                <th className="px-5 py-3 text-left text-xs text-gray-600 uppercase tracking-wider">Status</th>
                <th className="px-5 py-3 text-left text-xs text-gray-600 uppercase tracking-wider">Eval types</th>
                <th className="px-5 py-3 text-left text-xs text-gray-600 uppercase tracking-wider">Progress</th>
                <th className="px-5 py-3 text-left text-xs text-gray-600 uppercase tracking-wider">Score</th>
                <th className="px-5 py-3 text-left text-xs text-gray-600 uppercase tracking-wider">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {runs.map((run) => (
                <tr
                  key={run.id}
                  className="hover:bg-gray-800/40 transition-colors cursor-pointer"
                  onClick={() => window.location.href = `/eval-runs/${run.id}`}
                >
                  <td className="px-5 py-3.5 text-xs font-mono text-gray-400">{run.id.slice(0, 12)}...</td>
                  <td className="px-5 py-3.5 text-xs">
                    <StatusDot status={run.status} />
                    <span className="text-gray-300 capitalize">{run.status}</span>
                  </td>
                  <td className="px-5 py-3.5 text-xs text-gray-500">{run.eval_types.join(", ")}</td>
                  <td className="px-5 py-3.5">
                    {run.status === "running" ? (
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-20 bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: run.total_rows > 0 ? `${(run.completed_rows / run.total_rows) * 100}%` : "0%" }}
                          />
                        </div>
                        <span className="text-xs text-gray-500 tabular-nums">
                          {run.completed_rows}/{run.total_rows}
                        </span>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-600">{run.total_rows} rows</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <span className={clsx("text-sm font-semibold tabular-nums", scoreColor(run.overall_score))}>
                      {run.overall_score !== null ? run.overall_score.toFixed(1) : "—"}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-xs text-gray-600">
                    <span className="flex items-center gap-1">
                      <Clock size={10} />
                      {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
