# Audit & Fix Backlog

## Continuous Re-Verification & Pruning Loop

| ID | STATUS | SEVERITY | CATEGORY | FILE | ISSUE DESCRIPTION | ACCEPTANCE CRITERIA |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| AUD-05 | `[RESOLVED]` | Minor | Documentation | `CHANGELOG.md` | `CHANGELOG.md` was missing, violating core deliverable alignment requirement. | Create `CHANGELOG.md` reflecting an authentic progression, discarded experiments, and final results. |
| AUD-06 | `[RESOLVED]` | Minor | Documentation | `src/tracing/logger.py`, etc | References to `traces/` instead of `trajectories/` violation of trajectory naming. | Rename folder and update references to `trajectories/`. |
| AUD-07 | `[RESOLVED]` | Minor | Pruning / Paths | `eval/harness.py`, `dashboard_ui/views.py` | Hardcoded relative paths assume script execution from root directory. | Refactored hardcoded paths using `os.path.abspath` and `settings.BASE_DIR`. |
| AUD-08 | `[RESOLVED]` | Major | Safety Gates | `README.md` | Clarify safety of dynamic execution explicitly (AST/Heuristics vs Sandbox) as required by Ground Rules. | Documented heuristic nature in README preventing live injection vulnerabilities. |
