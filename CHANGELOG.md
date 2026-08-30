# Improvement Changelog

This changelog connects each iterative architectural decision with empirical evidence, tracking how the system evolved from a monolithic baseline to an autonomous multi-agent FSM, as required by the micro1 challenge guidelines.

| Stage | What We Tried and Why | Evidence | Decision / Learning |
| :--- | :--- | :--- | :--- |
| **Baseline** | Single-prompt Monolithic Reviewer (`groq/openai/gpt-oss-120b` / `Gemini Pro`) evaluating Git diff and test output. | 70.0% accuracy vs human ground truth. Failed 3/10 flawed architectures. | Established baseline bottleneck: static code reading cannot evaluate runtime concurrency or distributed constraints. |
| **Iteration 1** | *[Discarded Experiment]* Added eBPF typing speed and terminal navigation entropy tracker to evaluate candidate "fluency". | Generated high variance and unfair penalties due to natural interview nervousness, without correlating with final code quality. | **REMOVED:** Shifted telemetry strictly from "typing process" to **"Code Evolution & Context Alignment (Blast Radius & Module Reusability)"**. |
| **Iteration 2** | Implemented AST Blast Radius and Codebase Reusability Inspector. | Accuracy jumped to 80.0%. Successfully flagged redundant reimplementation of tax validators. | **KEPT:** High-signal architectural compliance measurement. |
| **Iteration 3** | Added Dynamic Load & Concurrency Simulator (evaluating race conditions, memory spikes, deadlocks, and event loop blocking). | Accuracy jumped to 90.0%. Caught distributed deadlocks and in-memory cache drift. | **KEPT:** Essential for distributed systems evaluation. |
| **Iteration 4** | Enforced provenance in evaluation verdicts and dynamic seniority rubrics. | Re-audit showed 100% compliance with Ground Truth citation and severity adaptation. | **KEPT:** Provides absolute auditability for human judges. |
| **Final Squad** | Connected 4 specialized agents to Deterministic FSM Engine. | **100.0% Hiring Alignment Accuracy** and **87.8/100 Fidelity Score**. | **CONSOLIDATED:** Final architecture submitted. |
