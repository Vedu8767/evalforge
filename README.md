diff --git a/README.md b/README.md
index 0fc738a..589d3c8 100644
--- a/README.md
+++ b/README.md
@@ -20,6 +20,29 @@ EvalForge is a production SaaS platform that lets AI teams automatically evaluat
 
 ---
 
+## Why this matters for India
+
+India is deploying LLMs into government, healthcare, legal, and education faster than anyone
+is testing them — and no Indian team has built evaluation infrastructure specifically for
+**Indic-language models, government AI deployments, and DPDP Act-grade data handling.**
+Global eval tools benchmark English chatbots; they weren't built for a health worker in Bihar
+getting AI-generated triage advice in Hindi, or a citizen asking a government scheme-navigation
+bot a question in Tamil.
+
+EvalForge closes that gap:
+
+- **Indic LLM evaluation** — hallucination and factual-accuracy scoring designed to hold up
+  across Hindi, Tamil, Bengali, and other Indian-language outputs, not just English benchmarks.
+- **High-stakes government use cases** — eval suites for healthcare triage, legal/scheme
+  guidance, and education platforms, where a wrong answer has real consequences.
+- **Culturally aware jailbreak testing** — the existing 10-probe / 5-category red-team suite,
+  extended to catch prompt-injection and roleplay bypasses framed in regional language and
+  cultural context.
+- **DPDP Act compliance scoring** — automated checks for how a model handles personal data in
+  its outputs, flagging responses that risk violating India's Digital Personal Data Protection Act.
+
+---
+
 ## Features
 
 | Feature | Description |
