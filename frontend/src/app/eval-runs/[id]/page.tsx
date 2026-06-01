"use client";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { evalRunsApi, type EvalRun, type EvalResult } from "@/lib/api";
import { useParams } from "next/navigation";
import { clsx } from "clsx";
import {
  CheckCircle, AlertTriangle, ChevronDown, ChevronUp, Download
} from "lucide-react";

function ScoreCircle({ score, label }: { score: number | null; label: string }) {
  const color =
    score === null ? "text-gray-600" :
    score >= 90 ? "text-emerald-400" :
    score >= 75 ? "text-green-400" :
    score >= 60 ? "text-yellow-400" : "text-red-400";
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={clsx("text-3xl font-bold tabular-nums", color)}>
        {score === null ? "—" : score.toFixed(1)}
      </div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: EvalRun["status"] }) {
  const map: Record<string, { color: string; label: string; dot: string }> = {
    queued:    { color: "text-gray-400",    label: "Queued",    dot: "bg-gray-500" },
    running:   { color: "text-blue-400",    label: "Running",   dot: "bg-blue-400 animate-pulse" },
    completed: { color: "text-emerald-400", label: "Completed", dot: "bg-emerald-400" },
    failed:    { color: "text-red-400",     label: "Failed",    dot: "bg-red-400" },
    cancelled: { color: "text-gray-500",    label: "Cancelled", dot: "bg-gray-600" },
  };
  const s = map[status] ?? map.queued;
  return (
    <div className={clsx("flex items-center gap-2 text-sm font-medium", s.color)}>
      <div className={clsx("w-2 h-2 rounded-full", s.dot)} />
      {s.label}
    </div>
  );
}

function VerdictBadge({ verdict }: { verdict: string | null }) {
  if (!verdict) return <span className="text-gray-600 text-xs">—</span>;
  const map: Record<string, string> = {
    correct:   "bg-emerald-900/40 text-emerald-300",
    partial:   "bg-yellow-900/40 text-yellow-300",
    incorrect: "bg-red-900/40 text-red-300",
    pass:      "bg-emerald-900/40 text-emerald-300",
    fail:      "bg-red-900/40 text-red-300",
  };
  return (
    <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium", map[verdict] ?? "bg-gray-800 text-gray-400")}>
      {verdict}
    </span>
  );
}

function ResultRow({ result }: { result: EvalResult }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <tr
        className="border-t border-gray-800 hover:bg-gray-800/40 cursor-pointer transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="px-4 py-3 text-xs text-gray-400 font-mono">{result.id.slice(0, 8)}</td>
        <td className="px-4 py-3 text-xs text-gray-300 max-w-xs truncate">{result.actual_output}</td>
        <td className="px-4 py-3">
          {result.hallucination_detected === null ? (
            <span className="text-gray-700 text-xs">—</span>
          ) : result.hallucination_detected ? (
            <span className="flex items-center gap-1 text-red-400 text-xs"><AlertTriangle size={12} /> Yes</span>
          ) : (
            <span className="flex items-center gap-1 text-emerald-400 text-xs"><CheckCircle size={12} /> No</span>
          )}
        </td>
        <td className="px-4 py-3"><VerdictBadge verdict={result.judge_verdict} /></td>
        <td className="px-4 py-3 text-xs text-gray-400 tabular-nums">
          {result.factual_score !== null ? `${(result.factual_score * 100).toFixed(0)}%` : "—"}
        </td>
        <td className="px-4 py-3 text-xs text-gray-500 tabular-nums">
          {result.latency_ms ? `${result.latency_ms}ms` : "—"}
        </td>
        <td className="px-4 py-3 text-gray-600">
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-gray-800 bg-gray-900/50">
          <td colSpan={7} className="px-6 py-4">
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <div className="text-gray-500 mb-1 font-medium">Full output</div>
                <div className="text-gray-300 bg-gray-800 rounded-lg p-3 font-mono whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                  {result.actual_output || "—"}
                </div>
              </div>
              <div className="space-y-3">
                {result.hallucination_reason && (
                  <div>
                    <div className="text-gray-500 mb-1 font-medium">Hallucination reason</div>
                    <div className="text-gray-300 bg-gray-800 rounded-lg p-3">{result.hallucination_reason}</div>
                  </div>
                )}
                {result.judge_reasoning && (
                  <div>
                    <div className="text-gray-500 mb-1 font-medium">Judge reasoning</div>
                    <div className="text-gray-300 bg-gray-800 rounded-lg p-3">{result.judge_reasoning}</div>
                  </div>
                )}
                {result.error && (
                  <div>
                    <div className="text-red-500 mb-1 font-medium">Error</div>
                    <div className="text-red-300 bg-red-900/20 rounded-lg p-3 font-mono">{result.error}</div>
                  </div>
                )}
                <div className="flex gap-4 text-gray-500">
                  <span>Tokens: {result.tokens_used ?? "—"}</span>
                  <span>Latency: {result.latency_ms ? `${result.latency_ms}ms` : "—"}</span>
                  {result.similarity_score != null && (
                    <span>Similarity: {((result.similarity_score) * 100).toFixed(1)}%</span>
                  )}
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function EvalRunDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const [liveResults, setLiveResults] = useState<any[]>([]);
  const [filterVerdict, setFilterVerdict] = useState("");
  const sseRef = useRef<EventSource | null>(null);

  const { data: run, refetch } = useQuery<EvalRun>({
    queryKey: ["eval-run", runId],
    queryFn: () => evalRunsApi.get(runId),
    refetchInterval: 3000,
  });

  const { data: results = [] } = useQuery<EvalResult[]>({
    queryKey: ["eval-results", runId, filterVerdict],
    queryFn: () => evalRunsApi.results(runId, { verdict: filterVerdict || undefined, limit: 100 }),
    enabled: run?.status === "completed" || run?.status === "failed",
  });

  useEffect(() => {
    if (run?.status !== "running" && run?.status !== "queued") return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const es = new EventSource(`${apiUrl}/eval-runs/${runId}/stream`);
    sseRef.current = es;
    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setLiveResults((prev) => [...prev.slice(-99), data]);
    };
    es.addEventListener("done", () => { es.close(); refetch(); });
    return () => es.close();
  }, [run?.status, runId, refetch]);

  const exportCSV = () => {
    if (!results.length) return;
    const headers = ["id", "actual_output", "hallucination_detected", "judge_verdict", "factual_score", "latency_ms"];
    const rows = results.map((r) => headers.map((h) => (r as any)[h] ?? "").join(","));
    const csv = [headers.join(","), ...rows].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = `eval-run-${runId.slice(0, 8)}.csv`;
    a.click();
  };

  if (!run) return <div className="p-8 text-gray-600 text-sm">Loading...</div>;

  const progress = run.total_rows > 0
    ? Math.round((run.completed_rows / run.total_rows) * 100)
    : 0;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-xl font-bold text-white font-mono">{runId.slice(0, 8)}...</h1>
            <StatusBadge status={run.status} />
          </div>
          <div className="text-sm text-gray-500">
            {run.eval_types.join(" · ")} · {run.total_rows} rows
          </div>
        </div>
        {run.status === "completed" && (
          <button
            onClick={exportCSV}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white border border-gray-700 rounded-lg px-3 py-2 transition-colors"
          >
            <Download size={14} /> Export CSV
          </button>
        )}
      </div>

      {(run.status === "running" || run.status === "queued") && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 mb-6">
          <div className="flex justify-between text-sm text-gray-400 mb-3">
            <span>Processing rows...</span>
            <span className="tabular-nums">{run.completed_rows} / {run.total_rows}</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-600 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          {liveResults.length > 0 && (
            <div className="mt-4 space-y-1 max-h-40 overflow-y-auto">
              {liveResults.slice(-10).map((r, i) => (
                <div key={i} className="flex items-center gap-3 text-xs">
                  {r.hallucination === false
                    ? <CheckCircle size={11} className="text-emerald-500 flex-shrink-0" />
                    : r.hallucination === true
                    ? <AlertTriangle size={11} className="text-red-500 flex-shrink-0" />
                    : <div className="w-3 h-3 rounded-full bg-gray-700 flex-shrink-0" />}
                  <span className="text-gray-400 truncate">{r.output}</span>
                  <span className="text-gray-600 flex-shrink-0">{r.latency_ms}ms</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {run.status === "completed" && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Overall",           value: run.overall_score },
            { label: "Hallucination-free", value: run.hallucination_score },
            { label: "Jailbreak resist.",  value: run.jailbreak_resistance_score },
            { label: "Factual accuracy",   value: run.factual_accuracy_score },
          ].map(({ label, value }) => (
            <div key={label} className="bg-gray-900 rounded-xl border border-gray-800 p-5 text-center">
              <ScoreCircle score={value} label={label} />
            </div>
          ))}
        </div>
      )}

      {run.status === "failed" && run.error_message && (
        <div className="bg-red-900/20 border border-red-800 rounded-xl p-4 mb-6 text-sm text-red-300">
          <strong>Error:</strong> {run.error_message}
        </div>
      )}

      {results.length > 0 && (
        <div className="bg-gray-900 rounded-xl border border-gray-800">
          <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
            <h2 className="text-sm font-medium text-white">{results.length} Results</h2>
            <select
              value={filterVerdict}
              onChange={(e) => setFilterVerdict(e.target.value)}
              className="bg-gray-800 border border-gray-700 text-sm text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none"
            >
              <option value="">All verdicts</option>
              <option value="correct">Correct</option>
              <option value="partial">Partial</option>
              <option value="incorrect">Incorrect</option>
            </select>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-600 uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">ID</th>
                  <th className="px-4 py-3 text-left">Output</th>
                  <th className="px-4 py-3 text-left">Hallucination</th>
                  <th className="px-4 py-3 text-left">Verdict</th>
                  <th className="px-4 py-3 text-left">Factual</th>
                  <th className="px-4 py-3 text-left">Latency</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {results.map((r) => <ResultRow key={r.id} result={r} />)}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
