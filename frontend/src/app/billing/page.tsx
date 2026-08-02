"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Check, Zap, Users, Shield } from "lucide-react";
import { clsx } from "clsx";

type Plan = {
  name: string;
  price_usd: number;
  price_inr: number;
  features: string[];
  eval_runs_per_month: number;
  team_members: number;
  api_access: boolean;
};

const planIcons: Record<string, any> = {
  Free: Zap,
  Pro: Shield,
  Team: Users,
};

const planColors: Record<string, string> = {
  Free: "border-gray-700",
  Pro: "border-indigo-500",
  Team: "border-purple-500",
};

const planHighlight: Record<string, string> = {
  Pro: "Most popular",
  Team: "Best for teams",
};

export default function BillingPage() {
  const [billing, setBilling] = useState<"monthly">("monthly");

  const { data: plansData } = useQuery({
    queryKey: ["plans"],
    queryFn: () => api.get("/billing/plans").then((r) => r.data.plans as Record<string, Plan>),
  });

  const checkoutMutation = useMutation({
    mutationFn: (plan: string) =>
      api.post("/billing/checkout", { plan }).then((r) => r.data),
    onSuccess: (data) => {
      window.location.href = data.checkout_url;
    },
    onError: (e: any) =>
      toast.error(e.response?.data?.detail || "Failed to start checkout"),
  });

  const portalMutation = useMutation({
    mutationFn: () => api.post("/billing/portal", {}).then((r) => r.data),
    onSuccess: (data) => {
      window.location.href = data.portal_url;
    },
    onError: () => toast.error("Could not open billing portal"),
  });

  if (!plansData) return null;

  const plans = Object.entries(plansData);

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-3xl font-bold text-white mb-3">Simple, transparent pricing</h1>
        <p className="text-gray-400">Start free. Upgrade when your team needs more.</p>
      </div>

      {/* Plan cards */}
      <div className="grid grid-cols-3 gap-6 mb-12">
        {plans.map(([planKey, plan]) => {
          const Icon = planIcons[plan.name] || Zap;
          const highlight = planHighlight[plan.name];
          const isFree = plan.price_inr === 0;

          return (
            <div
              key={planKey}
              className={clsx(
                "relative bg-gray-900 rounded-2xl border-2 p-6 flex flex-col",
                planColors[plan.name] || "border-gray-700",
                highlight && "ring-1 ring-indigo-500/30"
              )}
            >
              {highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                  {highlight}
                </div>
              )}

              <div className="mb-5">
                <div className={clsx(
                  "w-10 h-10 rounded-xl flex items-center justify-center mb-3",
                  planKey === "free" ? "bg-gray-800" :
                  planKey === "pro" ? "bg-indigo-600/20" : "bg-purple-600/20"
                )}>
                  <Icon size={18} className={
                    planKey === "free" ? "text-gray-400" :
                    planKey === "pro" ? "text-indigo-400" : "text-purple-400"
                  } />
                </div>
                <div className="text-lg font-semibold text-white">{plan.name}</div>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className="text-3xl font-bold text-white">₹{plan.price_inr.toLocaleString("en-IN")}</span>
                  {!isFree && <span className="text-gray-500 text-sm">/month</span>}
                  {isFree && <span className="text-gray-500 text-sm">forever</span>}
                </div>
              </div>

              <ul className="space-y-2.5 flex-1 mb-6">
                {plan.features.map((f: string) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-gray-300">
                    <Check size={14} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>

              {isFree ? (
                <div className="w-full text-center py-2.5 rounded-xl text-sm text-gray-600 border border-gray-800">
                  Current plan
                </div>
              ) : (
                <button
                  onClick={() => checkoutMutation.mutate(planKey)}
                  disabled={checkoutMutation.isPending}
                  className={clsx(
                    "w-full py-2.5 rounded-xl text-sm font-medium transition-colors",
                    planKey === "pro"
                      ? "bg-indigo-600 hover:bg-indigo-700 text-white"
                      : "bg-purple-600 hover:bg-purple-700 text-white"
                  )}
                >
                  {checkoutMutation.isPending ? "Loading..." : `Upgrade to ${plan.name}`}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Manage existing subscription */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-white mb-0.5">Manage subscription</div>
          <div className="text-xs text-gray-500">
            Update payment method, download invoices, or cancel anytime.
          </div>
        </div>
        <button
          onClick={() => portalMutation.mutate()}
          disabled={portalMutation.isPending}
          className="text-sm text-indigo-400 hover:text-indigo-300 border border-indigo-800/50 rounded-lg px-4 py-2 transition-colors"
        >
          {portalMutation.isPending ? "Opening..." : "Open billing portal →"}
        </button>
      </div>

      {/* FAQ */}
      <div className="mt-12">
        <h2 className="text-lg font-semibold text-white mb-6">Frequently asked questions</h2>
        <div className="grid grid-cols-2 gap-6">
          {[
            {
              q: "What counts as an eval run?",
              a: "One eval run = running your full dataset against one model endpoint. A 10-row dataset = 1 run regardless of how many eval types you choose.",
            },
            {
              q: "Can I cancel anytime?",
              a: "Yes. Cancel through the billing portal and you'll keep Pro access until the end of your billing period. No questions asked.",
            },
            {
              q: "What happens if I hit the free limit?",
              a: "New eval runs are blocked until the next month or until you upgrade. Your existing data is never deleted.",
            },
            {
              q: "Is my API key secure?",
              a: "Yes. All API keys are encrypted with AES-256 before storage. We never log or expose them in plaintext.",
            },
          ].map(({ q, a }) => (
            <div key={q} className="bg-gray-900 rounded-xl border border-gray-800 p-5">
              <div className="text-sm font-medium text-white mb-2">{q}</div>
              <div className="text-xs text-gray-500 leading-relaxed">{a}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
