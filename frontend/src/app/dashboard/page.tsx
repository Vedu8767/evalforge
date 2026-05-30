"use client";
import { useQuery } from "@tanstack/react-query";
import { evalRunsApi, type EvalRun } from "@/lib/api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from "recharts";
import { Play, AlertTriangle, Shield, CheckCircle, Clock, Plus } from "lucide-react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { clsx } from "clsx";

function scoreColor(score: number | null): string {
  if (score === null) return "text-gray-500";
  if (score >= 90) return "text-emerald-400";
  if (score >= 75) return "text-green-400";
  if (score >= 60) return "text-yellow-400";
  return "text-red-400";
}

function StatusBadge({ status }: { status: EvalRun["status"] }) {
  const map: Record<string, { color: string; label: string }> = {
    queued:    { color: "bg-gray-700 text-gray-300", label: "Queued" },
    running:   { color: "bg-blue-900/50 text-blue-300", label: "Running" },
    completed: { color: "bg-emerald-900/50 text-emerald-300", label: "Done" },
    failed:    { color: "bg-red-900/50 text-red-300", label: "Failed" },
    cancelled: { color: "bg-gray-700 text-gray-400", label: "Cancelled" },
  };
  const s = map[status] ?? map.queued;
  return (
    <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium", s.color)}>
      {s.label}
    </span>
  );
}

export default function DashboardPage() {
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["eval-runs"],
    queryFn: () => evalRunsApi.list({ limit: 20 }),
    refetchInterval: 5000, // poll every 5s for live updates
  });

  const completed = runs.filter((r) => r.status === "completed");
  const avgOverall = completed.length
    ? completed.reduce((s, r) => s + (r.overall_score ?? 0), 0) / completed.length
    : null;
  const avgHallucination = completed.length
    ? completed.reduce((s, r) => s + (r.hallucination_score ?? 0), 0) / completed.length
    : null;
  const avgJailbreak = completed.length
    ? completed.reduce((s, r) => s + (r.jailbreak_resistance_score ?? 0), 0) / completed.length
    : null;

  // Chart data — last 10 completed runs
  const chartData = completed.slice(-10).map((r, i) => ({
    run: `#${i + 1}`,
    overall: r.overall_score,
    hallucination: r.hallucination_score,
    jailbreak: r.jailbreak_resistance_score,
  }));

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">LLM health at a glance</p>
        </div>
        <Link
          href="/eval-runs/new"
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} /> New Eval Run
        </Link>
      </div>

      {/* Score Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Overall Score", value: avgOverall, icon: CheckCircle, desc: "Avg across all evals" },
          { label: "Hallucination-Free", value: avgHallucination, icon: AlertTriangle, desc: "% rows without hallucination" },
          { label: "Jailbreak Resistance", value: avgJailbreak, icon: Shield, desc: "% probes refused" },
          { label: "Total Runs", value: runs.length, icon: Play, desc: "All time", raw: true },
        ].map(({ label, value, icon: Icon, desc, raw }) => (
          <div key={label} className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">{label}</span>
              <Icon size={15} className="text-gray-600" />
            </div>
            <div className={clsx("text-3xl font-bold", raw ? "text-white" : scoreColor(value as number))}>
              {value === null ? "—" : raw ? value : `${(value as number).toFixed(1)}`}
              {!raw && value !== null && <span className="text-lg text-gray-500 ml-1">/ 100</span>}
            </div>
            <div className="text-xs text-gray-600 mt-1">{desc}</div>
          </div>
        ))}
      </div>

      {/* Chart */}
      {chartData.length > 1 && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 mb-8">
          <h2 className="text-sm font-medium text-gray-400 mb-4">Score trends — last {chartData.length} runs</h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="run" tick={{ fill: "#6b7280", fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fill: "#6b7280", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                labelStyle={{ color: "#e5e7eb" }}
              />
              <Line type="monotone" dataKey="overall" stroke="#818cf8" strokeWidth={2} dot={false} name="Overall" />
              <Line type="monotone" dataKey="hallucination" stroke="#34d399" strokeWidth={2} dot={false} name="Hallucination-free" />
              <Line type="monotone" dataKey="jailbreak" stroke="#f59e0b" strokeWidth={2} dot={false} name="Jailbreak resist." />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Recent Runs Table */}
      <div className="bg-gray-900 rounded-xl border border-gray-800">
        <div className="px-6 py-4 border-b border-gray-800">
          <h2 className="text-sm font-medium text-white">Recent Eval Runs</h2>
        </div>
        {isLoading ? (
          <div className="p-8 text-center text-gray-600">Loading...</div>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center">
            <Play size={32} className="text-gray-700 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No eval runs yet.</p>
            <Link href="/eval-runs/new" className="text-indigo-400 text-sm hover:underline mt-1 inline-block">
              Create your first eval run →
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {runs.map((run) => (
              <Link
                key={run.id}
                href={`/eval-runs/${run.id}`}
                className="flex items-center gap-4 px-6 py-4 hover:bg-gray-800/50 transition-colors"
              >
                <StatusBadge status={run.status} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-gray-200 truncate font-mono">{run.id.slice(0, 8)}...</div>
                  <div className="text-xs text-gray-500 mt-0.5">{run.eval_types.join(", ")}</div>
                </div>
                {run.status === "running" && (
                  <div className="text-xs text-blue-400">
                    {run.completed_rows}/{run.total_rows} rows
                  </div>
                )}
                <div className={clsx("text-sm font-semibold tabular-nums", scoreColor(run.overall_score))}>
                  {run.overall_score !== null ? `${run.overall_score.toFixed(1)}` : "—"}
                </div>
                <div className="text-xs text-gray-600 flex items-center gap-1">
                  <Clock size={11} />
                  {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
