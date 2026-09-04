"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { evalRunsApi, modelsApi, datasetsApi } from "@/lib/api";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ChevronRight, ChevronLeft, Play } from "lucide-react";
import { clsx } from "clsx";

const EVAL_TYPES = [
  { id: "hallucination", label: "Hallucination Detection", desc: "Self-consistency + LLM-judge to find fabricated claims", color: "indigo" },
  { id: "jailbreak", label: "Jailbreak Resistance", desc: "Run 10 adversarial probes across 5 attack categories", color: "red" },
  { id: "factual", label: "Factual Accuracy", desc: "LLM-judge compares output vs expected answer", color: "emerald" },
  { id: "regression", label: "Regression Testing", desc: "Diff this run against a pinned baseline", color: "yellow" },
];

export default function NewEvalRunPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    model_endpoint_id: "",
    dataset_id: "",
    eval_types: ["factual"],
    concurrency: 5,
  });

  const { data: models = [] } = useQuery({ queryKey: ["models"], queryFn: modelsApi.list });
  const { data: datasets = [] } = useQuery({ queryKey: ["datasets"], queryFn: datasetsApi.list });

  const createMutation = useMutation({
    mutationFn: evalRunsApi.create,
    onSuccess: (run) => {
      toast.success("Eval run started!");
      router.push(`/eval-runs/${run.id}`);
    },
    onError: () => toast.error("Failed to start eval run"),
  });

  const toggleEvalType = (type: string) => {
    setForm((f) => ({
      ...f,
      eval_types: f.eval_types.includes(type)
        ? f.eval_types.filter((t) => t !== type)
        : [...f.eval_types, type],
    }));
  };

  const canNext = () => {
    if (step === 1) return !!form.model_endpoint_id;
    if (step === 2) return !!form.dataset_id;
    if (step === 3) return form.eval_types.length > 0;
    return true;
  };

  const steps = ["Model", "Dataset", "Eval Types", "Launch"];

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-2">New Eval Run</h1>
      <p className="text-gray-600 dark:text-gray-400 text-sm mb-8">Configure and launch an evaluation in 4 steps</p>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-10">
        {steps.map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div className={clsx(
              "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold",
              i + 1 < step ? "bg-indigo-600 text-white" :
              i + 1 === step ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500" :
              "bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-600"
            )}>
              {i + 1 < step ? "✓" : i + 1}
            </div>
            <span className={clsx("text-sm", i + 1 === step ? "text-white" : "text-gray-500 dark:text-gray-600")}>{s}</span>
            {i < steps.length - 1 && <ChevronRight size={14} className="text-gray-400 dark:text-gray-700 ml-1" />}
          </div>
        ))}
      </div>

      {/* Step 1: Model */}
      {step === 1 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Select Model Endpoint</h2>
          {models.length === 0 ? (
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-8 text-center">
              <p className="text-gray-500 text-sm">No models registered yet.</p>
              <a href="/models" className="text-indigo-400 text-sm hover:underline mt-1 inline-block">Register a model →</a>
            </div>
          ) : (
            <div className="space-y-3">
              {models.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setForm((f) => ({ ...f, model_endpoint_id: m.id }))}
                  className={clsx(
                    "w-full text-left p-4 rounded-xl border transition-colors",
                    form.model_endpoint_id === m.id
                      ? "border-indigo-500 bg-indigo-600/10"
                      : "border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-gray-300 dark:hover:border-gray-700"
                  )}
                >
                  <div className="text-sm font-medium text-white">{m.name}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{m.provider} · {m.model_name}</div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Step 2: Dataset */}
      {step === 2 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Select Dataset</h2>
          <div className="space-y-3">
            {datasets.map((d) => (
              <button
                key={d.id}
                onClick={() => setForm((f) => ({ ...f, dataset_id: d.id }))}
                className={clsx(
                  "w-full text-left p-4 rounded-xl border transition-colors",
                  form.dataset_id === d.id
                    ? "border-indigo-500 bg-indigo-600/10"
                    : "border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-gray-300 dark:hover:border-gray-700"
                )}
              >
                <div className="text-sm font-medium text-white">{d.name}</div>
                <div className="text-xs text-gray-500 mt-0.5">{d.row_count} rows · {d.type}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step 3: Eval Types */}
      {step === 3 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Choose Eval Types</h2>
          <div className="space-y-3">
            {EVAL_TYPES.map((e) => {
              const selected = form.eval_types.includes(e.id);
              return (
                <button
                  key={e.id}
                  onClick={() => toggleEvalType(e.id)}
                  className={clsx(
                    "w-full text-left p-4 rounded-xl border transition-colors flex items-start gap-4",
                    selected ? "border-indigo-500 bg-indigo-600/10" : "border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-gray-300 dark:hover:border-gray-700"
                  )}
                >
                  <div className={clsx(
                    "w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5",
                    selected ? "border-indigo-500 bg-indigo-600" : "border-gray-400 dark:border-gray-600"
                  )}>
                    {selected && <span className="text-white text-xs">✓</span>}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-white">{e.label}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{e.desc}</div>
                  </div>
                </button>
              );
            })}
          </div>
          <div className="mt-4">
            <label className="text-sm text-gray-600 dark:text-gray-400 block mb-2">Concurrency (parallel LLM calls)</label>
            <input
              type="range" min={1} max={10} value={form.concurrency}
              onChange={(e) => setForm((f) => ({ ...f, concurrency: +e.target.value }))}
              className="w-full accent-indigo-600"
            />
            <div className="text-xs text-gray-500 mt-1">{form.concurrency} concurrent calls</div>
          </div>
        </div>
      )}

      {/* Step 4: Review */}
      {step === 4 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Review & Launch</h2>
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 space-y-4">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Model</span>
              <span className="text-white">{models.find(m => m.id === form.model_endpoint_id)?.name}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Dataset</span>
              <span className="text-white">{datasets.find(d => d.id === form.dataset_id)?.name}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Eval types</span>
              <span className="text-white">{form.eval_types.join(", ")}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Concurrency</span>
              <span className="text-white">{form.concurrency} parallel calls</span>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between mt-8">
        <button
          onClick={() => setStep((s) => s - 1)}
          disabled={step === 1}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronLeft size={16} /> Back
        </button>

        {step < 4 ? (
          <button
            onClick={() => setStep((s) => s + 1)}
            disabled={!canNext()}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Next <ChevronRight size={16} />
          </button>
        ) : (
          <button
            onClick={() => createMutation.mutate(form)}
            disabled={createMutation.isPending}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <Play size={15} />
            {createMutation.isPending ? "Launching..." : "Launch Eval Run"}
          </button>
        )}
      </div>
    </div>
  );
}
