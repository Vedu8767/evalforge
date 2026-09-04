"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { modelsApi } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Zap, CheckCircle, XCircle, Cpu } from "lucide-react";
import { clsx } from "clsx";

const PROVIDERS = [
  { id: "openai",    label: "OpenAI",    url: "https://api.openai.com/v1", models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"] },
  { id: "anthropic", label: "Anthropic", url: "https://api.anthropic.com", models: ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"] },
  { id: "custom",    label: "Custom",    url: "",                          models: [] },
];

const defaultForm = {
  name: "", provider: "openai", base_url: "https://api.openai.com/v1",
  model_name: "gpt-4o-mini", api_key: "", system_prompt: "",
  temperature: 0.0, max_tokens: 1000,
};

export default function ModelsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(defaultForm);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; output?: string; latency_ms?: number; error?: string } | null>>({});

  const { data: models = [], isLoading } = useQuery({ queryKey: ["models"], queryFn: modelsApi.list });

  const createMutation = useMutation({
    mutationFn: modelsApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["models"] });
      toast.success("Model endpoint registered!");
      setShowForm(false);
      setForm(defaultForm);
    },
    onError: () => toast.error("Failed to create model endpoint"),
  });

  const deleteMutation = useMutation({
    mutationFn: modelsApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["models"] }); toast.success("Deleted"); },
  });

  const handleTest = async (id: string) => {
    setTestResults((t) => ({ ...t, [id]: null }));
    try {
      const result = await modelsApi.test(id, "Say 'Hello from EvalForge!' in exactly those words.");
      setTestResults((t) => ({ ...t, [id]: result }));
    } catch {
      setTestResults((t) => ({ ...t, [id]: { success: false, error: "Test failed" } }));
    }
  };

  const selectedProvider = PROVIDERS.find((p) => p.id === form.provider);

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Model Endpoints</h1>
          <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">Register any OpenAI-compatible LLM to evaluate</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          <Plus size={16} /> Register Model
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 mb-6">
          <h2 className="text-sm font-semibold text-white mb-5">Register new model endpoint</h2>
          <div className="grid grid-cols-2 gap-4">
            {/* Provider */}
            <div className="col-span-2">
              <label className="text-xs text-gray-600 dark:text-gray-400 block mb-1.5">Provider</label>
              <div className="flex gap-2">
                {PROVIDERS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setForm((f) => ({
                      ...f, provider: p.id,
                      base_url: p.url,
                      model_name: p.models[0] || "",
                    }))}
                    className={clsx(
                      "px-4 py-2 rounded-lg text-sm border transition-colors",
                      form.provider === p.id
                        ? "border-indigo-500 bg-indigo-600/10 text-indigo-300"
                        : "border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-gray-400 dark:hover:border-gray-600"
                    )}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs text-gray-600 dark:text-gray-400 block mb-1.5">Display name</label>
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="GPT-4o Production"
                className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs text-gray-600 dark:text-gray-400 block mb-1.5">Model name</label>
              {selectedProvider && selectedProvider.models.length > 0 ? (
                <select
                  value={form.model_name}
                  onChange={(e) => setForm((f) => ({ ...f, model_name: e.target.value }))}
                  className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                >
                  {selectedProvider.models.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              ) : (
                <input
                  value={form.model_name}
                  onChange={(e) => setForm((f) => ({ ...f, model_name: e.target.value }))}
                  placeholder="your-model-name"
                  className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                />
              )}
            </div>

            <div className="col-span-2">
              <label className="text-xs text-gray-600 dark:text-gray-400 block mb-1.5">Base URL</label>
              <input
                value={form.base_url}
                onChange={(e) => setForm((f) => ({ ...f, base_url: e.target.value }))}
                className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
              />
            </div>

            <div className="col-span-2">
              <label className="text-xs text-gray-600 dark:text-gray-400 block mb-1.5">API Key</label>
              <input
                type="password"
                value={form.api_key}
                onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
                placeholder="sk-..."
                className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none font-mono"
              />
              <p className="text-xs text-gray-500 dark:text-gray-600 mt-1">Encrypted with AES-256 before storage. Never returned in plaintext.</p>
            </div>

            <div className="col-span-2">
              <label className="text-xs text-gray-600 dark:text-gray-400 block mb-1.5">System prompt (optional)</label>
              <textarea
                value={form.system_prompt}
                onChange={(e) => setForm((f) => ({ ...f, system_prompt: e.target.value }))}
                rows={3}
                placeholder="You are a helpful assistant..."
                className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none resize-none"
              />
            </div>

            <div>
              <label className="text-xs text-gray-600 dark:text-gray-400 block mb-1.5">Temperature: {form.temperature}</label>
              <input type="range" min={0} max={2} step={0.1} value={form.temperature}
                onChange={(e) => setForm((f) => ({ ...f, temperature: parseFloat(e.target.value) }))}
                className="w-full accent-indigo-600"
              />
            </div>

            <div>
              <label className="text-xs text-gray-600 dark:text-gray-400 block mb-1.5">Max tokens</label>
              <input
                type="number" min={1} max={32000} value={form.max_tokens}
                onChange={(e) => setForm((f) => ({ ...f, max_tokens: +e.target.value }))}
                className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
              />
            </div>
          </div>

          <div className="flex gap-3 mt-5">
            <button
              onClick={() => createMutation.mutate(form)}
              disabled={!form.name || !form.api_key || createMutation.isPending}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white px-5 py-2 rounded-lg text-sm font-medium"
            >
              {createMutation.isPending ? "Saving..." : "Save endpoint"}
            </button>
            <button onClick={() => setShowForm(false)} className="text-gray-600 dark:text-gray-400 hover:text-white text-sm px-3">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Model list */}
      {isLoading ? (
        <div className="text-gray-500 dark:text-gray-600 text-sm">Loading...</div>
      ) : models.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-12 text-center">
          <Cpu size={32} className="text-gray-400 dark:text-gray-700 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No model endpoints yet.</p>
          <button onClick={() => setShowForm(true)} className="text-indigo-400 text-sm hover:underline mt-1">
            Register your first model →
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {models.map((m) => {
            const testResult = testResults[m.id];
            return (
              <div key={m.id} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-white">{m.name}</span>
                      <span className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded-full">{m.provider}</span>
                    </div>
                    <div className="text-xs text-gray-500">{m.model_name} · {m.base_url}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-600 font-mono mt-0.5">{m.api_key_masked}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTest(m.id)}
                      className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400 hover:text-white border border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600 rounded-lg px-3 py-1.5 transition-colors"
                    >
                      <Zap size={12} /> Test
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(m.id)}
                      className="text-gray-500 dark:text-gray-600 hover:text-red-400 p-1.5 rounded-lg transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Test result */}
                {testResult !== undefined && (
                  <div className={clsx(
                    "mt-3 p-3 rounded-lg text-xs",
                    testResult === null ? "bg-gray-100 dark:bg-gray-800 text-gray-500" :
                    testResult.success ? "bg-emerald-900/20 border border-emerald-800/50" :
                    "bg-red-900/20 border border-red-800/50"
                  )}>
                    {testResult === null ? (
                      "Testing connection..."
                    ) : testResult.success ? (
                      <div className="flex items-start gap-2">
                        <CheckCircle size={12} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <div className="text-emerald-300 font-medium mb-0.5">Connected · {testResult.latency_ms}ms</div>
                          <div className="text-gray-600 dark:text-gray-400 font-mono">{testResult.output}</div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-red-300">
                        <XCircle size={12} className="flex-shrink-0" />
                        {testResult.error}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
