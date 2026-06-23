"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { datasetsApi } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Upload, Trash2, Database, ChevronDown, ChevronUp, Eye } from "lucide-react";
import { clsx } from "clsx";

const defaultForm = { name: "", description: "", type: "factual" };
const DATASET_TYPES = ["factual", "qa", "jailbreak", "custom"];

export default function DatasetsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(defaultForm);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [rowsData, setRowsData] = useState<Record<string, any[]>>({});

  const { data: datasets = [], isLoading } = useQuery({
    queryKey: ["datasets"],
    queryFn: datasetsApi.list,
    refetchOnMount: "always",
    staleTime: 0,
  });

  const createMutation = useMutation({
    mutationFn: datasetsApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      toast.success("Dataset created!");
      setShowForm(false);
      setForm(defaultForm);
    },
    onError: () => toast.error("Failed to create dataset"),
  });

  const deleteMutation = useMutation({
    mutationFn: datasetsApi.delete || ((id: string) => Promise.resolve()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      toast.success("Dataset deleted");
    },
    onError: () => toast.error("Failed to delete dataset"),
  });

  const handleUpload = async (datasetId: string, file: File) => {
    // Validate CSV format before uploading
    const text = await file.text();
    const lines = text.trim().split("\n");
    if (lines.length < 2) {
      toast.error("CSV must have a header row and at least one data row");
      return;
    }
    const headers = lines[0].toLowerCase().split(",").map(h => h.trim().replace(/"/g, ""));
    if (!headers.includes("input_prompt")) {
      toast.error(`CSV must have an 'input_prompt' column. Found: ${headers.join(", ")}`);
      return;
    }

    setUploading(datasetId);
    try {
      await datasetsApi.uploadCSV(datasetId, file);
      qc.invalidateQueries({ queryKey: ["datasets"] });
      toast.success(`Uploaded ${lines.length - 1} rows successfully!`);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Upload failed — check CSV format");
    } finally {
      setUploading(null);
    }
  };

  const handleViewRows = async (datasetId: string) => {
    if (expandedId === datasetId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(datasetId);
    if (!rowsData[datasetId]) {
      try {
        const rows = await datasetsApi.rows(datasetId, { limit: 5 });
        setRowsData(prev => ({ ...prev, [datasetId]: rows }));
      } catch {
        toast.error("Failed to load rows");
      }
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Datasets</h1>
          <p className="text-gray-400 text-sm mt-1">
            Upload CSV files with prompts to evaluate your LLMs
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} /> New Dataset
        </button>
      </div>

      {/* CSV format hint */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6 text-xs text-gray-400">
        <div className="font-medium text-gray-300 mb-2">📋 CSV Format Required</div>
        <div className="font-mono bg-gray-800 rounded-lg p-3 text-green-400">
          input_prompt,expected_output,context<br/>
          "What is the capital of France?","Paris",""<br/>
          "Who wrote Hamlet?","Shakespeare",""
        </div>
        <div className="mt-2 text-gray-500">
          Only <span className="text-indigo-400">input_prompt</span> is required.
          {" "}<span className="text-gray-400">expected_output</span> and{" "}
          <span className="text-gray-400">context</span> are optional.
        </div>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 mb-6">
          <h2 className="text-sm font-semibold text-white mb-4">Create new dataset</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-400 block mb-1.5">Dataset name *</label>
              <input
                value={form.name}
                onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="General Knowledge QA"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1.5">Type</label>
              <select
                value={form.type}
                onChange={(e) => setForm(f => ({ ...f, type: e.target.value }))}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
              >
                {DATASET_TYPES.map(t => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-400 block mb-1.5">Description (optional)</label>
              <input
                value={form.description}
                onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))}
                placeholder="What is this dataset for?"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button
              onClick={() => createMutation.mutate(form)}
              disabled={!form.name || createMutation.isPending}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white px-5 py-2 rounded-lg text-sm font-medium"
            >
              {createMutation.isPending ? "Creating..." : "Create dataset"}
            </button>
            <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-white text-sm px-3">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Dataset list */}
      {isLoading ? (
        <div className="text-gray-600 text-sm">Loading...</div>
      ) : datasets.length === 0 ? (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-12 text-center">
          <Database size={32} className="text-gray-700 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No datasets yet.</p>
          <button onClick={() => setShowForm(true)} className="text-indigo-400 text-sm hover:underline mt-1">
            Create your first dataset →
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {datasets.map((d: any) => (
            <div key={d.id} className="bg-gray-900 rounded-xl border border-gray-800">
              <div className="p-5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-indigo-600/10 rounded-lg flex items-center justify-center">
                    <Database size={16} className="text-indigo-400" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-white">{d.name}</div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {d.type} · {d.row_count} rows
                      {d.description && ` · ${d.description}`}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {/* View rows */}
                  <button
                    onClick={() => handleViewRows(d.id)}
                    className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white border border-gray-700 hover:border-gray-600 rounded-lg px-3 py-1.5 transition-colors"
                  >
                    <Eye size={12} />
                    {expandedId === d.id ? "Hide" : "Preview"}
                    {expandedId === d.id ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  </button>

                  {/* Upload CSV */}
                  <label className={clsx(
                    "flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 transition-colors cursor-pointer",
                    uploading === d.id
                      ? "text-gray-600 border-gray-800"
                      : "text-gray-400 hover:text-white border-gray-700 hover:border-gray-600"
                  )}>
                    <Upload size={12} />
                    {uploading === d.id ? "Uploading..." : "Upload CSV"}
                    <input
                      type="file"
                      accept=".csv"
                      className="hidden"
                      disabled={uploading === d.id}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleUpload(d.id, file);
                        e.target.value = "";
                      }}
                    />
                  </label>

                  {/* Delete */}
                  <button
                    onClick={() => deleteMutation.mutate(d.id)}
                    className="text-gray-600 hover:text-red-400 p-1.5 rounded-lg transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Row preview */}
              {expandedId === d.id && (
                <div className="border-t border-gray-800 p-4">
                  {!rowsData[d.id] ? (
                    <div className="text-gray-600 text-xs">Loading rows...</div>
                  ) : rowsData[d.id].length === 0 ? (
                    <div className="text-gray-600 text-xs">
                      No rows yet. Upload a CSV to add data.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="text-xs text-gray-500 mb-2">
                        Showing first {rowsData[d.id].length} rows:
                      </div>
                      {rowsData[d.id].map((row: any, i: number) => (
                        <div key={row.id || i} className="bg-gray-800 rounded-lg p-3 text-xs">
                          <div className="text-gray-300 font-medium mb-1">
                            Q: {row.input_prompt}
                          </div>
                          {row.expected_output && (
                            <div className="text-gray-500">
                              A: {row.expected_output}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
