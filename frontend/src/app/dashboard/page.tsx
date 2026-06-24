"use client";
import { useQuery } from "@tanstack/react-query";
import { evalRunsApi } from "@/lib/api";
import Link from "next/link";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { Plus, TrendingUp, Shield, AlertTriangle, Play } from "lucide-react";
import { clsx } from "clsx";

function ScoreCard({
  label, value, icon: Icon, color, sub
}: {
  label: string;
  value: number | null;
  icon: any;
  color: string;
  sub: string;
}) {
  const scoreColor =
    value === null ? "text-gray-600" :
    value >= 90 ? "text-emerald-400" :
    value >= 75 ? "text-green-400" :
    value >= 60 ? "text-yellow-400" : "text-red-400";

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-gray-500 uppercase tracking-wider font-medium">{label}</span>
        <Icon size={14} className={color} />
      </div>
      <div className={clsx("text-3xl font-bold tabular-nums mb-1", scoreColor)}>
        {value === null ? "—" : value.toFixed(1)}
      </div>
      <div className="text-xs text-gray-600">{sub}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    completed: "bg-emerald-900/40 text-emerald-300",
    running:   "bg-blue-900/40 text-blue-300 animate-pulse",
    queued:    "bg-gray-800 text-gray-400",
    failed:    "bg-red-900/40 text-red-300",
  };
  return (
    <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium", map[status] ?? "bg-gray-800 text-gray-400")}>
      {status}
    </span>
  );
}

export default function DashboardPage() {
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["eval-runs-dashboard"],
    queryFn: () => evalRunsApi.list({ limit: 20 }),
    refetchInterval: 10000,
    refetchOnMount: "always",
    staleTime: 0,
  });

  const completedRuns = runs.filter((r: any) => r.status === "completed");

  // Compute aggregate stats from latest completed runs
  const latestScores = completedRuns.slice(0, 5);
  const avgOverall = latestScores.length
    ? latestScores.reduce((s: number, r: any) => s + (r.overall_score || 0), 0) / latestScores.length
    : null;
  const avgHallucination = latestScores.filter((r: any) => r.hallucination_score !== null).length
    ? latestScores.filter((r: any) => r.hallucination_score !== null)
        .reduce((s: number, r: any) => s + (r.hallucination_score || 0), 0) /
      latestScores.filter((r: any) => r.hallucination_score !== null).length
    : null;
  const avgFactual = latestScores.filter((r: any) => r.factual_accuracy_score !== null).length
    ? latestScores.filter((r: any) => r.factual_accuracy_score !== null)
        .reduce((s: number, r: any) => s + (r.factual_accuracy_score || 0), 0) /
      latestScores.filter((r: any) => r.factual_accuracy_score !== null).length
    : null;

  // Chart data — score trend over time
  const chartData = completedRuns
    .slice(0, 10)
    .reverse()
    .map((r: any, i: number) => ({
      run: `Run ${i + 1}`,
      overall: r.overall_score ? parseFloat(r.overall_score.toFixed(1)) : 0,
      factual: r.factual_accuracy_score ? parseFloat(r.factual_accuracy_score.toFixed(1)) : 0,
      hallucination: r.hallucination_score ? parseFloat(r.hallucination_score.toFixed(1)) : 0,
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

      {/* Score cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <ScoreCard
          label="Overall Score"
          value={avgOverall}
          icon={TrendingUp}
          color="text-indigo-400"
          sub="Avg across last 5 evals"
        />
        <ScoreCard
          label="Hallucination-Free"
          value={avgHallucination}
          icon={AlertTriangle}
          color="text-yellow-400"
          sub="% rows without hallucination"
        />
        <ScoreCard
          label="Jailbreak Resist."
          value={null}
          icon={Shield}
          color="text-red-400"
          sub="% probes refused"
        />
        <ScoreCard
          label="Total Runs"
          value={runs.length}
          icon={Play}
          color="text-emerald-400"
          sub="All time"
        />
      </div>

      {/* Score trend chart */}
      {chartData.length >= 2 && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 mb-8">
          <div className="text-sm font-medium text-white mb-4">Score Trend</div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="run" tick={{ fontSize: 11, fill: "#6b7280" }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#6b7280" }} />
              <Tooltip
                contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: "8px" }}
                labelStyle={{ color: "#9ca3af" }}
              />
              <Legend />
              <Line type="monotone" dataKey="overall" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} name="Overall" />
              <Line type="monotone" dataKey="factual" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} name="Factual" />
              <Line type="monotone" dataKey="hallucination" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} name="Hallucination-free" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Recent eval runs */}
      <div className="bg-gray-900 rounded-xl border border-gray-800">
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <div className="text-sm font-medium text-white">Recent Eval Runs</div>
          <Link href="/eval-runs" className="text-xs text-indigo-400 hover:text-indigo-300">
            View all →
          </Link>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-gray-600 text-sm">Loading...</div>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center">
            <Play size={28} className="text-gray-700 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No eval runs yet.</p>
            <Link href="/eval-runs/new" className="text-indigo-400 text-sm hover:underline mt-1 inline-block">
              Create your first eval run →
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {runs.slice(0, 8).map((run: any) => (
              <Link
                key={run.id}
                href={`/eval-runs/${run.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-gray-800/40 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div>
                    <div className="text-sm text-white font-mono">{run.id.slice(0, 8)}...</div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {run.eval_types?.join(" · ")} · {run.total_rows} rows
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {run.overall_score !== null && (
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
    </div>
  );
}
