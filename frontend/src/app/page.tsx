import Link from "next/link";
import {
  Shield, Zap, Github, ArrowRight, Languages, Landmark,
  FileCheck, AlertTriangle, Stethoscope, Scale, GraduationCap,
} from "lucide-react";

const PILLARS = [
  {
    icon: Languages,
    title: "Built for Indic LLMs",
    body: "Hallucination and factual-accuracy scoring designed to hold up across Hindi, Tamil, Bengali, and other Indian-language model outputs — not just English benchmarks.",
  },
  {
    icon: Landmark,
    title: "High-Stakes Government Use Cases",
    body: "Purpose-built eval suites for the domains where a wrong answer actually costs something: healthcare triage, legal guidance, and public education deployments.",
  },
  {
    icon: Shield,
    title: "Jailbreak Testing, Culturally Aware",
    body: "10 adversarial probes across 5 attack categories, extended to catch prompt-injection and roleplay bypasses framed in regional language and cultural context.",
  },
  {
    icon: FileCheck,
    title: "DPDP Act Compliance Scoring",
    body: "Automated checks for how a model handles personal data in its outputs — flagging responses that risk violating India's Digital Personal Data Protection Act.",
  },
];

const USE_CASES = [
  { icon: Stethoscope, label: "Rural healthcare triage bots", note: "Hallucination-checked before a symptom-checker goes live." },
  { icon: Scale, label: "Legal & scheme-navigation assistants", note: "Factual accuracy scored against the actual scheme text." },
  { icon: GraduationCap, label: "Government education platforms", note: "Red-teamed for jailbreaks before student-facing rollout." },
];

export default function RootPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* Nav */}
      <header className="border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
              <Zap size={15} className="text-white" />
            </div>
            <span className="font-semibold text-white tracking-tight">EvalForge</span>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="https://github.com/Vedu8767/evalforge"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-white transition-colors"
            >
              <Github size={16} /> GitHub
            </a>
            <Link
              href="/login"
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              Sign in
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-1.5 bg-indigo-900/30 border border-indigo-800/50 text-indigo-300 text-xs font-medium px-3 py-1 rounded-full mb-6">
          <Shield size={12} /> AI safety infrastructure, built in India
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold text-white tracking-tight leading-tight mb-5">
          Evaluation infrastructure for India&apos;s AI moment
        </h1>
        <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto mb-9 leading-relaxed">
          India is deploying LLMs into government, healthcare, legal, and education faster than
          anyone is testing them. EvalForge is the evaluation and red-teaming layer that checks
          for hallucination, jailbreak resistance, and DPDP Act compliance — before a model
          reaches a citizen.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link
            href="/login"
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-5 py-2.5 rounded-lg transition-colors"
          >
            Try the platform <ArrowRight size={16} />
          </Link>
          <a
            href="https://github.com/Vedu8767/evalforge"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 border border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600 text-gray-700 dark:text-gray-300 font-medium px-5 py-2.5 rounded-lg transition-colors"
          >
            <Github size={16} /> View source
          </a>
        </div>
      </section>

      {/* Problem statement */}
      <section className="max-w-4xl mx-auto px-6 pb-16">
        <div className="bg-red-900/10 border border-red-900/30 rounded-2xl p-6 flex gap-4">
          <AlertTriangle className="text-red-400 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <div className="text-sm font-semibold text-red-300 mb-1">The gap</div>
            <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
              No Indian team has built evaluation infrastructure specifically for Indic-language
              models, government AI deployments, and DPDP-Act-grade data handling. Global eval
              tools benchmark English chatbots — they weren&apos;t built for a health worker in
              Bihar getting AI-generated triage advice in Hindi.
            </p>
          </div>
        </div>
      </section>

      {/* Pillars */}
      <section className="max-w-6xl mx-auto px-6 pb-20">
        <h2 className="text-center text-sm font-semibold text-indigo-400 uppercase tracking-wide mb-10">
          What makes it India-specific
        </h2>
        <div className="grid sm:grid-cols-2 gap-5">
          {PILLARS.map(({ icon: Icon, title, body }) => (
            <div key={title} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
              <div className="w-10 h-10 bg-indigo-600/20 rounded-xl flex items-center justify-center mb-4">
                <Icon size={18} className="text-indigo-400" />
              </div>
              <h3 className="text-white font-semibold mb-2">{title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Use cases */}
      <section className="max-w-4xl mx-auto px-6 pb-24">
        <h2 className="text-center text-sm font-semibold text-indigo-400 uppercase tracking-wide mb-10">
          Where this matters most
        </h2>
        <div className="space-y-3">
          {USE_CASES.map(({ icon: Icon, label, note }) => (
            <div
              key={label}
              className="flex items-center gap-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-5 py-4"
            >
              <div className="w-9 h-9 bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center flex-shrink-0">
                <Icon size={16} className="text-gray-600 dark:text-gray-400" />
              </div>
              <div>
                <div className="text-sm font-medium text-white">{label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{note}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer CTA */}
      <footer className="border-t border-gray-200 dark:border-gray-800">
        <div className="max-w-4xl mx-auto px-6 py-10 text-center">
          <p className="text-sm text-gray-500 mb-4">
            Built end-to-end — FastAPI, Celery, Redis, PostgreSQL (pgvector), Next.js.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-5 py-2.5 rounded-lg transition-colors"
          >
            Get started <ArrowRight size={16} />
          </Link>
        </div>
      </footer>
    </div>
  );
}
