"use client";
import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { datasetsApi } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Upload, Trash2, Database, FileText, ChevronRight } from "lucide-react";
import { clsx } from "clsx";
import Link from "next/link";

const DATASET_TYPES = [
  { id: "qa", label: "Q&A", desc: "Prompt + expected answer pairs" },
  { id: "factual", label: "Factual", desc: "Fact-check style prompts" },
  { id: "jailbreak", label: "Jailbreak", desc: "Safety / adversarial prompts" },
  { id: "custom", label: "Custom", desc: "Any prompt collection" },
];

export default function DatasetsPage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [uploadTarget, setUploadTarget] = useState<string | null>(null);
  const [newDs, setNewDs] = useState({ name: "", type: "qa", description: "" });

  const { data: datasets = [], isLoading } = useQuery({
    queryKey: ["datasets"],
    queryFn: datasetsApi.list,
  });

  const createMutation = useMutation({
    mutationFn: datasetsApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      toast.success("Dataset created!");
      setShowCreate(false);
      setNewDs({ name: "", type: "qa", description: "" });
    },
  });

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !uploadTarget) return;
    try {
      const result = await datasetsApi.uploadCSV(uploadTarget, file);
      toast.success(`Imported ${result.rows_created} rows`);
      qc.invalidateQueries({ queryKey: ["datasets"] });
    } catch {
      toast.error("Upload failed. Check your CSV columns.");
    }
    if (fileRef.current) fileRef.current.value = "";
    setUploadTarget(null);
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Datasets</h1>
          <p className="text-gray-400 text-sm mt-1">Collections of prompts and expected outputs for evaluation</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          <Plus size={16} /> New Dataset
        </button>
      </div>

      {/* CSV format hint */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6 text-xs text-gray-500">
        <div className="flex items-center gap-2 mb-2 text-gray-400 font-medium">
          <FileText size={13} /> CSV / JSONL format
        </div>
        <div className="font-mono bg-gray-800 rounded-lg p-3 text-gray-400">
          input_prompt,expected_output,context,tags<br/>
          "What is Python?","A programming language","","factual,easy"<br/>
          "Capital of Japan?","Tokyo","",""
        </div>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 mb-6">
          <h2 className="text-sm font-semibold text-white mb-4">Create dataset</h2>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-gray-400 block mb-1.5">Name</label>
              <input
                value={newDs.name}
                onChange={(e) => setNewDs((d) => ({ ...d, name: e.target.value }))}
                placeholder="e.g. Product FAQ Test Set"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1.5">Type</label>
              <div className="grid grid-cols-2 gap-2">
                {DATASET_TYPES.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setNewDs((d) => ({ ...d, type: t.id }))}
                    className={clsx(
                      "text-left p-3 rounded-lg border text-xs transition-colors",
                      newDs.type === t.id
                        ? "border-indigo-500 bg-indigo-600/10 text-indigo-300"
                        : "border-gray-700 text-gray-400 hover:border-gray-600"
                    )}
                  >
                    <div className="font-medium">{t.label}</div>
                    <div className="text-gray-600 mt-0.5">{t.desc}</div>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1.5">Description (optional)</label>
              <input
                value={newDs.description}
                onChange={(e) => setNewDs((d) => ({ ...d, description: e.target.value }))}
                placeholder="What this dataset tests..."
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
              />
            </div>
          </div>
          <div className="flex gap-3 mt-5">
            <button
              onClick={() => createMutation.mutate(newDs)}
              disabled={!newDs.name || createMutation.isPending}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white px-5 py-2 rounded-lg text-sm font-medium"
            >
              {createMutation.isPending ? "Creating..." : "Create dataset"}
            </button>
            <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-white text-sm px-3">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Hidden file input */}
      <input ref={fileRef} type="file" accept=".csv,.jsonl" className="hidden" onChange={handleFileUpload} />

      {/* Dataset list */}
      {isLoading ? (
        <div className="text-gray-600 text-sm">Loading...</div>
      ) : datasets.length === 0 ? (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-12 text-center">
          <Database size={32} className="text-gray-700 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No datasets yet.</p>
          <button onClick={() => setShowCreate(true)} className="text-indigo-400 text-sm hover:underline mt-1">
            Create your first dataset →
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {datasets.map((ds) => (
            <div key={ds.id} className="bg-gray-900 rounded-xl border border-gray-800 p-5 flex items-center justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-white">{ds.name}</span>
                  <span className="text-xs bg-gray-800 text-gray-500 px-2 py-0.5 rounded-full">{ds.type}</span>
                </div>
                {ds.description && <div className="text-xs text-gray-500 mb-1">{ds.description}</div>}
                <div className="text-xs text-gray-600">
                  {ds.row_count} rows · Created {new Date(ds.created_at).toLocaleDateString()}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { setUploadTarget(ds.id); fileRef.current?.click(); }}
                  className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white border border-gray-700 hover:border-gray-600 rounded-lg px-3 py-1.5 transition-colors"
                >
                  <Upload size={12} /> Upload CSV
                </button>
                <Link
                  href={`/datasets/${ds.id}`}
                  className="flex items-center gap-1 text-xs text-gray-400 hover:text-white px-2 py-1.5"
                >
                  View rows <ChevronRight size={12} />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
