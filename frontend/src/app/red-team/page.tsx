"use client";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { modelsApi } from "@/lib/api";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Shield, AlertTriangle, CheckCircle, Play, ChevronDown, ChevronUp } from "lucide-react";
import { clsx } from "clsx";

const PROBE_CATEGORIES = [
  { id: "prompt_injection", label: "Prompt Injection", color: "text-red-400", bg: "bg-red-900/20 border-red-800/50", description: "Tests if the model ignores its instructions when asked to." },
  { id: "roleplay_bypass", label: "Roleplay Bypass", color: "text-orange-400", bg: "bg-orange-900/20 border-orange-800/50", description: "Tests if fictional framing makes the model ignore safety guidelines." },
  { id: "many_shot", label: "Many-Shot Priming", color: "text-yellow-400", bg: "bg-yellow-900/20 border-yellow-800/50", description: "Tests if fake Q&A history primes the model into compliance." },
  { id: "competing_objectives", label: "Competing Objectives", color: "text-purple-400", bg: "bg-purple-900/20 border-purple-800/50", description: "Tests if the model complies when asked to summarize harmful content." },
  { id: "hypothetical", label: "Hypothetical Framing", color: "text-blue-400", bg: "bg-blue-900/20 border-blue-800/50", description: "Tests if academic or hypothetical framing bypasses safety." },
];

const PROBES = [
  { id: "pi_001", category: "prompt_injection", name: "Instruction Override", risk: "high" },
  { id: "pi_002", category: "prompt_injection", name: "System Override", risk: "high" },
  { id: "rp_001", category: "roleplay_bypass", name: "DAN Prompt", risk: "critical" },
  { id: "rp_002", category: "roleplay_bypass", name: "Evil Character", risk: "critical" },
  { id: "rp_003", category: "roleplay_bypass", name: "Fictional Framing", risk: "high" },
  { id: "ms_001", category: "many_shot", name: "Fake Q&A Priming", risk: "medium" },
  { id: "co_001", category: "competing_objectives", name: "Summarize Harmful Doc", risk: "high" },
  { id: "hyp_001", category: "hypothetical", name: "Academic Framing", risk: "medium" },
  { id: "hyp_002", category: "hypothetical", name: "Hypothetical World", risk: "high" },
  { id: "ts_001", category: "token_smuggling", name: "Obfuscated Request", risk: "medium" },
];

const RISK_COLOR: Record<string, string> = {
  critical: "text-red-400 bg-red-900/30",
  high: "text-orange-400 bg-orange-900/30",
  medium: "text-yellow-400 bg-yellow-900/30",
  low: "text-green-400 bg-green-900/30",
};

export default function RedTeamPage() {
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedProbes, setSelectedProbes] = useState<string[]>(PROBES.map(p => p.id));
  const [results, setResults] = useState<any | null>(null);
  const [expandedProbe, setExpandedProbe] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const { data: models = [] } = useQuery({
    queryKey: ["models"],
    queryFn: modelsApi.list,
  });

  const toggleProbe = (id: string) => {
    setSelectedProbes(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    );
  };

  const runRedTeam = async () => {
    if (!selectedModel) { toast.error("Select a model first"); return; }
    if (selectedProbes.length === 0) { toast.error("Select at least one probe"); return; }

    setRunning(true);
    setResults(null);
    try {
      const res = await api.post("/eval-runs", {
        model_endpoint_id: selectedModel,
        dataset_id: null,
        eval_types: ["jailbreak"],
        probe_ids: selectedProbes,
        concurrency: 2,
      });
      toast.success("Red team run started! Check Eval Runs for results.");
      setResults({ run_id: res.data.id, status: "queued" });
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to start red team run");
    } finally {
      setRunning(false);
    }
  };

  const resistanceScore = results?.resistance_score;

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 bg-red-600/20 rounded-xl flex items-center justify-center">
            <Shield size={18} className="text-red-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Red Team Testing</h1>
        </div>
        <p className="text-gray-400 text-sm">
          Test your LLM against adversarial probes across 5 jailbreak attack categories.
          A resistant model should refuse all 10 probes.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left — config */}
        <div className="col-span-2 space-y-5">

          {/* Model selection */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <div className="text-sm font-medium text-white mb-3">Target Model</div>
            {models.length === 0 ? (
              <div className="text-xs text-gray-500">
                No models registered.{" "}
                <a href="/models" className="text-indigo-400 hover:underline">Register one →</a>
              </div>
            ) : (
              <select
                value={selectedModel}
                onChange={e => setSelectedModel(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="">Select a model...</option>
                {models.map((m: any) => (
                  <option key={m.id} value={m.id}>{m.name} ({m.model_name})</option>
                ))}
              </select>
            )}
          </div>

          {/* Probe categories */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm font-medium text-white">Attack Probes</div>
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedProbes(PROBES.map(p => p.id))}
                  className="text-xs text-indigo-400 hover:text-indigo-300"
                >
                  Select all
                </button>
                <span className="text-gray-700">·</span>
                <button
                  onClick={() => setSelectedProbes([])}
                  className="text-xs text-gray-500 hover:text-gray-300"
                >
                  Clear
                </button>
              </div>
            </div>

            <div className="space-y-2">
              {PROBE_CATEGORIES.map(cat => {
                const catProbes = PROBES.filter(p => p.category === cat.id);
                const selectedCount = catProbes.filter(p => selectedProbes.includes(p.id)).length;

                return (
                  <div key={cat.id} className={clsx("rounded-lg border p-3", cat.bg)}>
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className={clsx("text-xs font-medium", cat.color)}>{cat.label}</span>
                        <span className="text-xs text-gray-600 ml-2">{cat.description}</span>
                      </div>
                      <span className="text-xs text-gray-500">{selectedCount}/{catProbes.length}</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {catProbes.map(probe => (
                        <button
                          key={probe.id}
                          onClick={() => toggleProbe(probe.id)}
                          className={clsx(
                            "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all",
                            selectedProbes.includes(probe.id)
                              ? "border-indigo-500 bg-indigo-600/20 text-indigo-300"
                              : "border-gray-700 text-gray-500 hover:border-gray-600"
                          )}
                        >
                          <span className={clsx("w-1.5 h-1.5 rounded-full", RISK_COLOR[probe.risk]?.split(" ")[0].replace("text", "bg"))} />
                          {probe.name}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Run button */}
          <button
            onClick={runRedTeam}
            disabled={running || !selectedModel || selectedProbes.length === 0}
            className="w-full flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed text-white py-3 rounded-xl text-sm font-medium transition-colors"
          >
            <Play size={16} />
            {running ? "Starting red team run..." : `Run ${selectedProbes.length} probes`}
          </button>

          {/* Result queued notice */}
          {results?.run_id && (
            <div className="bg-indigo-900/20 border border-indigo-800/50 rounded-xl p-4 text-sm text-indigo-300">
              ✅ Red team run queued! Go to{" "}
              <a href="/eval-runs" className="underline hover:text-indigo-200">Eval Runs</a>{" "}
              to see live results as probes complete.
            </div>
          )}
        </div>

        {/* Right — info panel */}
        <div className="space-y-4">
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <div className="text-sm font-medium text-white mb-3">How it works</div>
            <div className="space-y-3 text-xs text-gray-400">
              <div className="flex gap-2">
                <span className="text-indigo-400 font-bold">1.</span>
                Each probe sends an adversarial prompt designed to bypass safety guidelines
              </div>
              <div className="flex gap-2">
                <span className="text-indigo-400 font-bold">2.</span>
                An LLM judge evaluates whether the model complied or refused
              </div>
              <div className="flex gap-2">
                <span className="text-indigo-400 font-bold">3.</span>
                Resistance score = % of probes refused (100% = fully resistant)
              </div>
            </div>
          </div>

          <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <div className="text-sm font-medium text-white mb-3">Risk Levels</div>
            <div className="space-y-2">
              {["critical", "high", "medium", "low"].map(risk => (
                <div key={risk} className="flex items-center gap-2">
                  <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium", RISK_COLOR[risk])}>
                    {risk}
                  </span>
                  <span className="text-xs text-gray-500">
                    {risk === "critical" ? "Most dangerous attack vectors" :
                     risk === "high" ? "Commonly exploited in production" :
                     risk === "medium" ? "Requires specific conditions" :
                     "Low-risk informational probes"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <div className="text-sm font-medium text-white mb-1">Selected probes</div>
            <div className="text-3xl font-bold text-white">{selectedProbes.length}</div>
            <div className="text-xs text-gray-500">of {PROBES.length} total</div>
          </div>
        </div>
      </div>
    </div>
  );
}
