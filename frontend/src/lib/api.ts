import axios from "axios";
import { getSession } from "next-auth/react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: API_URL });

// Attach JWT token from NextAuth session to every request
api.interceptors.request.use(async (config) => {
  const session = await getSession();
  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`;
  }
  return config;
});

// ─── Types ──────────────────────────────────────────────────────────────────

export type EvalRun = {
  id: string;
  dataset_id: string;
  model_endpoint_id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  eval_types: string[];
  total_rows: number;
  completed_rows: number;
  overall_score: number | null;
  hallucination_score: number | null;
  jailbreak_resistance_score: number | null;
  factual_accuracy_score: number | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
};

export type EvalResult = {
  id: string;
  dataset_row_id: string;
  actual_output: string;
  hallucination_detected: boolean | null;
  hallucination_confidence: number | null;
  hallucination_reason: string | null;
  jailbreak_succeeded: boolean | null;
  factual_score: number | null;
  judge_verdict: string | null;
  judge_reasoning: string | null;
  latency_ms: number | null;
  tokens_used: number | null;
  error: string | null;
  created_at: string;
};

export type ModelEndpoint = {
  id: string;
  name: string;
  provider: string;
  base_url: string;
  model_name: string;
  api_key_masked: string;
  system_prompt: string | null;
  temperature: number;
  max_tokens: number;
  created_at: string;
};

export type Dataset = {
  id: string;
  name: string;
  description: string | null;
  type: string;
  row_count: number;
  created_at: string;
};


// ─── API Functions ───────────────────────────────────────────────────────────

// Eval Runs
export const evalRunsApi = {
  list: (params?: { status?: string; limit?: number }) =>
    api.get<EvalRun[]>("/eval-runs", { params }).then((r) => r.data),

  get: (id: string) =>
    api.get<EvalRun>(`/eval-runs/${id}`).then((r) => r.data),

  create: (data: {
    dataset_id: string;
    model_endpoint_id: string;
    eval_types: string[];
    concurrency?: number;
  }) => api.post<EvalRun>("/eval-runs", data).then((r) => r.data),

  results: (id: string, params?: { verdict?: string; limit?: number }) =>
    api.get<EvalResult[]>(`/eval-runs/${id}/results`, { params }).then((r) => r.data),

  cancel: (id: string) => api.delete(`/eval-runs/${id}`),
};

// Model Endpoints
export const modelsApi = {
  list: () => api.get<ModelEndpoint[]>("/model-endpoints").then((r) => r.data),
  create: (data: any) => api.post<ModelEndpoint>("/model-endpoints", data).then((r) => r.data),
  test: (id: string, prompt?: string) =>
    api.post(`/model-endpoints/${id}/test`, { prompt }).then((r) => r.data),
  delete: (id: string) => api.delete(`/model-endpoints/${id}`),
};

// Datasets
export const datasetsApi = {
  list: () => api.get<Dataset[]>("/datasets").then((r) => r.data),
  create: (data: any) => api.post<Dataset>("/datasets", data).then((r) => r.data),
  uploadCSV: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`/datasets/${id}/upload`, form).then((r) => r.data);
  },
  rows: (id: string, params?: { limit?: number; offset?: number }) =>
    api.get(`/datasets/${id}/rows`, { params }).then((r) => r.data),
};
