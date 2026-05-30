"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Bell, Trash2, Plus, Shield, CreditCard, Users } from "lucide-react";
import { clsx } from "clsx";

type AlertRule = {
  id: string; name: string; metric: string; operator: string;
  threshold: number; notify_email: string[]; enabled: boolean; created_at: string;
};

const METRICS = [
  { id: "overall_score", label: "Overall Score" },
  { id: "hallucination_score", label: "Hallucination-free %" },
  { id: "jailbreak_resistance_score", label: "Jailbreak Resistance" },
  { id: "factual_accuracy_score", label: "Factual Accuracy" },
];

const OPERATORS = [
  { id: "lt", label: "drops below (<)" },
  { id: "gt", label: "rises above (>)" },
  { id: "lte", label: "is at or below (≤)" },
  { id: "gte", label: "is at or above (≥)" },
];

export default function SettingsPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"alerts" | "billing" | "team">("alerts");
  const [showAlertForm, setShowAlertForm] = useState(false);
  const [alertForm, setAlertForm] = useState({
    name: "", metric: "overall_score", operator: "lt",
    threshold: 70, notify_email: [""], notify_slack_webhook: "",
  });

  const { data: alerts = [] } = useQuery<AlertRule[]>({
    queryKey: ["alerts"],
    queryFn: () => api.get("/alerts").then((r) => r.data),
  });

  const createAlert = useMutation({
    mutationFn: (data: any) => api.post("/alerts", data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      toast.success("Alert rule created");
      setShowAlertForm(false);
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Failed"),
  });

  const deleteAlert = useMutation({
    mutationFn: (id: string) => api.delete(`/alerts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const tabs = [
    { id: "alerts", label: "Alert Rules", icon: Bell },
    { id: "billing", label: "Billing", icon: CreditCard },
    { id: "team", label: "Team", icon: Users },
  ] as const;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>

      {/* Tabs */}
      <div className="flex gap-1 mb-8 bg-gray-900 rounded-xl border border-gray-800 p-1 w-fit">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
              tab === id ? "bg-gray-800 text-white" : "text-gray-500 hover:text-gray-300"
            )}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* Alert Rules */}
      {tab === "alerts" && (
        <div>
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-semibold text-white">Alert Rules</h2>
              <p className="text-xs text-gray-500 mt-0.5">Get notified when eval scores breach a threshold</p>
            </div>
            <button
              onClick={() => setShowAlertForm(!showAlertForm)}
              className="flex items-center gap-2 text-sm text-indigo-400 hover:text-indigo-300 border border-indigo-800/50 hover:border-indigo-700 rounded-lg px-3 py-2 transition-colors"
            >
              <Plus size={14} /> New Alert
            </button>
          </div>

          {showAlertForm && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 mb-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 block mb-1.5">Alert name</label>
                  <input
                    value={alertForm.name}
                    onChange={(e) => setAlertForm((f) => ({ ...f, name: e.target.value }))}
                    placeholder="Low jailbreak resistance"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1.5">Metric</label>
                  <select
                    value={alertForm.metric}
                    onChange={(e) => setAlertForm((f) => ({ ...f, metric: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                  >
                    {METRICS.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1.5">Condition</label>
                  <select
                    value={alertForm.operator}
                    onChange={(e) => setAlertForm((f) => ({ ...f, operator: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                  >
                    {OPERATORS.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1.5">Threshold (0–100)</label>
                  <input
                    type="number" min={0} max={100} value={alertForm.threshold}
                    onChange={(e) => setAlertForm((f) => ({ ...f, threshold: +e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1.5">Notify email</label>
                  <input
                    type="email" value={alertForm.notify_email[0]}
                    onChange={(e) => setAlertForm((f) => ({ ...f, notify_email: [e.target.value] }))}
                    placeholder="team@company.com"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1.5">Slack webhook (optional)</label>
                  <input
                    value={alertForm.notify_slack_webhook}
                    onChange={(e) => setAlertForm((f) => ({ ...f, notify_slack_webhook: e.target.value }))}
                    placeholder="https://hooks.slack.com/..."
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500 mt-3 mb-4">
                <Shield size={12} />
                Alert fires: when <span className="text-white mx-1">{METRICS.find(m=>m.id===alertForm.metric)?.label}</span>
                {OPERATORS.find(o=>o.id===alertForm.operator)?.label}
                <span className="text-white mx-1">{alertForm.threshold}</span>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => createAlert.mutate(alertForm)}
                  disabled={!alertForm.name || createAlert.isPending}
                  className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm font-medium"
                >
                  Create alert
                </button>
                <button onClick={() => setShowAlertForm(false)} className="text-gray-500 text-sm px-3">Cancel</button>
              </div>
            </div>
          )}

          {alerts.length === 0 ? (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-8 text-center">
              <Bell size={28} className="text-gray-700 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">No alert rules configured.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {alerts.map((alert) => (
                <div key={alert.id} className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-white mb-0.5">{alert.name}</div>
                    <div className="text-xs text-gray-500">
                      {METRICS.find(m => m.id === alert.metric)?.label} {OPERATORS.find(o => o.id === alert.operator)?.label} {alert.threshold}
                      {alert.notify_email.length > 0 && ` · ${alert.notify_email[0]}`}
                    </div>
                  </div>
                  <button
                    onClick={() => deleteAlert.mutate(alert.id)}
                    className="text-gray-600 hover:text-red-400 p-2 rounded-lg"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Billing */}
      {tab === "billing" && (
        <div className="space-y-4">
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-white">Current Plan</h2>
                <p className="text-xs text-gray-500 mt-0.5">Free tier — 50 eval runs/month</p>
              </div>
              <span className="bg-gray-800 text-gray-300 text-xs px-3 py-1 rounded-full font-medium">Free</span>
            </div>
            <div className="grid grid-cols-3 gap-3 mb-4">
              {[
                { label: "Eval runs", value: "50 / mo", limit: true },
                { label: "Team members", value: "1", limit: true },
                { label: "Baselines", value: "1", limit: true },
              ].map(({ label, value, limit }) => (
                <div key={label} className="bg-gray-800 rounded-lg p-3 text-center">
                  <div className="text-sm font-semibold text-white">{value}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{label}</div>
                </div>
              ))}
            </div>
            <a
              href="#"
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
            >
              <CreditCard size={14} /> Upgrade to Pro — $29/mo
            </a>
          </div>
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 text-xs text-gray-500">
            <div className="font-medium text-gray-400 mb-2">Pro includes</div>
            <ul className="space-y-1">
              {["Unlimited eval runs", "10 team members", "Unlimited baselines", "Alert rules", "API access for CI/CD", "90 day data retention"].map(f => (
                <li key={f} className="flex items-center gap-2">
                  <span className="text-emerald-500">✓</span> {f}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Team */}
      {tab === "team" && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-1">Team Members</h2>
          <p className="text-xs text-gray-500 mb-5">Upgrade to Pro to invite team members.</p>
          <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg">
            <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center text-xs font-semibold text-white">
              Y
            </div>
            <div>
              <div className="text-sm text-white">You</div>
              <div className="text-xs text-gray-500">Owner</div>
            </div>
          </div>
          <button className="mt-4 flex items-center gap-2 text-sm text-gray-500 border border-dashed border-gray-700 rounded-lg px-4 py-3 w-full justify-center hover:border-gray-600 hover:text-gray-400 transition-colors">
            <Plus size={14} /> Invite teammate (Pro only)
          </button>
        </div>
      )}
    </div>
  );
}
