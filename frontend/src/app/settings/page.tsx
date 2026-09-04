"use client";
import { useState } from "react";
import { useSession } from "next-auth/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
  User, Bell, CreditCard, Users, Plus, Trash2,
  Shield, Mail, Webhook
} from "lucide-react";
import { clsx } from "clsx";
import Link from "next/link";

type Tab = "profile" | "alerts" | "team" | "billing";

const TABS: { id: Tab; label: string; icon: any }[] = [
  { id: "profile", label: "Profile", icon: User },
  { id: "alerts", label: "Alert Rules", icon: Bell },
  { id: "team", label: "Team", icon: Users },
  { id: "billing", label: "Billing", icon: CreditCard },
];

function ProfileTab() {
  const { data: session } = useSession();

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-sm font-semibold text-white mb-4">Account Information</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-500 block mb-1.5">Full name</label>
            <div className="bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-700 dark:text-gray-300">
              {session?.user?.name || "—"}
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1.5">Email</label>
            <div className="bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2">
              <Mail size={12} className="text-gray-500 dark:text-gray-600" />
              {session?.user?.email || "—"}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-sm font-semibold text-white mb-1">API Access</h2>
        <p className="text-xs text-gray-500 mb-4">
          Use these endpoints to integrate EvalForge into your CI/CD pipeline.
        </p>
        <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-3 font-mono text-xs text-gray-600 dark:text-gray-400 space-y-1">
          <div>POST {process.env.NEXT_PUBLIC_API_URL}/eval-runs</div>
          <div>GET  {process.env.NEXT_PUBLIC_API_URL}/eval-runs/{"{id}"}</div>
        </div>
        <a
          href={`${process.env.NEXT_PUBLIC_API_URL}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-indigo-400 hover:underline mt-3 inline-block"
        >
          View full API documentation →
        </a>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
          <Shield size={14} className="text-emerald-400" />
          Security
        </h2>
        <p className="text-xs text-gray-500 mb-3">
          Passwords are hashed with bcrypt. API keys are encrypted with AES-256 before storage.
        </p>
      </div>
    </div>
  );
}

function AlertsTab() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    metric: "overall_score",
    operator: "lt",
    threshold: 70,
  });

  const { data: alerts = [], isLoading } = useQuery({
    queryKey: ["alert-rules"],
    queryFn: () => api.get("/alerts").then(r => r.data),
    refetchOnMount: "always",
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post("/alerts", data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alert-rules"] });
      toast.success("Alert rule created!");
      setShowForm(false);
    },
    onError: () => toast.error("Failed to create alert rule"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/alerts/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alert-rules"] });
      toast.success("Alert deleted");
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-white">Alert Rules</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Get notified when eval scores cross a threshold
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded-lg text-xs font-medium"
        >
          <Plus size={14} /> New Alert
        </button>
      </div>

      {showForm && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
          <div className="grid grid-cols-2 gap-3 mb-4">
            <input
              placeholder="Alert name (e.g. Low overall score)"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="col-span-2 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
            />
            <select
              value={form.metric}
              onChange={e => setForm(f => ({ ...f, metric: e.target.value }))}
              className="bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
            >
              <option value="overall_score">Overall Score</option>
              <option value="hallucination_score">Hallucination-Free %</option>
              <option value="jailbreak_resistance_score">Jailbreak Resistance %</option>
              <option value="factual_accuracy_score">Factual Accuracy %</option>
            </select>
            <div className="flex gap-2">
              <select
                value={form.operator}
                onChange={e => setForm(f => ({ ...f, operator: e.target.value }))}
                className="bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none w-20"
              >
                <option value="lt">{"<"}</option>
                <option value="lte">{"≤"}</option>
                <option value="gt">{">"}</option>
                <option value="gte">{"≥"}</option>
              </select>
              <input
                type="number"
                value={form.threshold}
                onChange={e => setForm(f => ({ ...f, threshold: +e.target.value }))}
                className="bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none flex-1"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => createMutation.mutate(form)}
              disabled={!form.name || createMutation.isPending}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-xs font-medium"
            >
              Create
            </button>
            <button onClick={() => setShowForm(false)} className="text-gray-600 dark:text-gray-400 text-xs px-3">
              Cancel
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-gray-500 dark:text-gray-600 text-xs">Loading...</div>
      ) : alerts.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-8 text-center">
          <Bell size={24} className="text-gray-400 dark:text-gray-700 mx-auto mb-2" />
          <p className="text-gray-500 text-xs">No alert rules configured</p>
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((alert: any) => (
            <div key={alert.id} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 flex items-center justify-between">
              <div>
                <div className="text-sm text-white font-medium">{alert.name}</div>
                <div className="text-xs text-gray-500 mt-0.5 font-mono">
                  {alert.metric} {alert.operator === "lt" ? "<" : alert.operator === "gt" ? ">" : alert.operator} {alert.threshold}
                </div>
              </div>
              <button
                onClick={() => deleteMutation.mutate(alert.id)}
                className="text-gray-500 dark:text-gray-600 hover:text-red-400 p-1.5"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TeamTab() {
  const { data: session } = useSession();

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-sm font-semibold text-white mb-1">Workspace Members</h2>
        <p className="text-xs text-gray-500 mb-4">
          Free plan supports 1 member. Upgrade to Team for up to 10 members.
        </p>
        <div className="flex items-center gap-3 bg-gray-100 dark:bg-gray-800 rounded-lg p-3">
          <div className="w-8 h-8 bg-indigo-600/30 rounded-full flex items-center justify-center">
            <User size={14} className="text-indigo-400" />
          </div>
          <div className="flex-1">
            <div className="text-sm text-gray-700 dark:text-gray-300">{session?.user?.name}</div>
            <div className="text-xs text-gray-500 dark:text-gray-600">{session?.user?.email}</div>
          </div>
          <span className="text-xs bg-indigo-900/40 text-indigo-300 px-2 py-0.5 rounded-full">Owner</span>
        </div>
      </div>
      <Link
        href="/billing"
        className="block bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 text-sm text-indigo-400 hover:text-indigo-300 text-center"
      >
        Upgrade to Team plan for more members →
      </Link>
    </div>
  );
}

function BillingTab() {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-8 text-center">
      <CreditCard size={28} className="text-gray-400 dark:text-gray-700 mx-auto mb-3" />
      <p className="text-gray-600 dark:text-gray-400 text-sm mb-1">Manage your subscription</p>
      <p className="text-gray-500 dark:text-gray-600 text-xs mb-4">View plans, upgrade, or manage billing</p>
      <Link
        href="/billing"
        className="inline-block bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2 rounded-lg text-sm font-medium"
      >
        Go to Billing →
      </Link>
    </div>
  );
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("profile");

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-1">Settings</h1>
      <p className="text-gray-600 dark:text-gray-400 text-sm mb-8">Manage your account, alerts, and team</p>

      <div className="flex gap-1 mb-6 border-b border-gray-200 dark:border-gray-800">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
              activeTab === id
                ? "border-indigo-500 text-white"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            )}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {activeTab === "profile" && <ProfileTab />}
      {activeTab === "alerts" && <AlertsTab />}
      {activeTab === "team" && <TeamTab />}
      {activeTab === "billing" && <BillingTab />}
    </div>
  );
}
