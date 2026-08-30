"""Tool: Concurrency & Distributed Load Performance Simulator with Calibrated Severity."""

import re
from src.core.domain import CandidateSubmission, ScenarioSpec, LoadSimulationResult


class LoadSimulator:
    """Evaluates behavioral performance of diffs under high-throughput concurrent load.
    
    Produces graduated severity signals (0.0-1.0) instead of binary pass/fail,
    enabling the critic to compute continuous penalty scores.
    """

    @staticmethod
    def simulate(submission: CandidateSubmission, spec: ScenarioSpec) -> LoadSimulationResult:
        full_diff = submission.full_diff or "\n".join(fc.diff_content for fc in submission.file_changes)
        sla_ms = spec.requirements.latency_p95_sla_ms
        target_rps = spec.requirements.concurrency_target_rps
        max_mem = spec.requirements.max_memory_mb

        throughput = float(target_rps)
        # Default baseline latency: 50% of the SLA target (healthy operation)
        p95 = sla_ms * 0.50
        p99 = sla_ms * 0.80
        error_rate = 0.0
        deadlock = False
        peak_memory_mb = 64.0
        details = []
        severity_signals = []

        # Check 1: In-memory local cache (@lru_cache) on horizontal multi-replica services
        if "@lru_cache" in full_diff:
            error_rate = 22.5
            p95 = sla_ms * 1.30
            details.append("Inconsistency detected across multi-instance nodes due to uncoordinated local @lru_cache.")
            severity_signals.append(0.65)

        # Check 2: In-memory mass data processing (.all() + sum/loop in Python) vs DB aggregation
        if ".all()" in full_diff and ("sum(" in full_diff or "for " in full_diff):
            peak_memory_mb = 1024.0
            p95 = sla_ms * 1.80
            p99 = sla_ms * 3.50
            details.append(f"Memory exhaustion: Peak {peak_memory_mb}MB exceeded SLA of {max_mem}MB.")
            severity_signals.append(0.55)

        # Check 3: Async event loop blocking (synchronous HTTP requests / time.sleep in async route)
        if re.search(r"\brequests\.(get|post|put|delete|patch|request)\b", full_diff) and "async def" in full_diff:
            throughput = target_rps * 0.10
            p95 = max(3200.0, sla_ms * 10.0)
            p99 = max(6500.0, sla_ms * 20.0)
            error_rate = 35.0
            details.append("Event loop blocked by synchronous requests inside async handler; concurrency collapsed.")
            severity_signals.append(0.80)

        # Check 4: Distributed Deadlock (Inverted lock acquisition order)
        if "lock_a" in full_diff and "lock_b" in full_diff and "acquire_lock" in full_diff:
            deadlock = True
            error_rate = 45.0
            p95 = 15000.0
            details.append("Distributed deadlock detected under concurrent opposing transactions.")
            severity_signals.append(1.0)

        # Check 5: Non-idempotent processing or unhandled balance race condition
        if "balance -=" in full_diff and "select_for_update" not in full_diff and "with_for_update" not in full_diff:
            error_rate = 18.0
            details.append("Race condition: Balance mutation without row-level lock (SELECT FOR UPDATE) or atomic transaction.")
            severity_signals.append(0.70)

        # Check 6: Thundering Herd Cache Invalidation
        if "ttl=60" in full_diff and "xfetch" not in full_diff and "lock" not in full_diff:
            p95 = sla_ms * 1.25
            details.append("Minor latency spike on cache expiration (thundering herd risk under high concurrency).")
            severity_signals.append(0.15)

        # Check 7: SQL Injection via string formatting
        if "f\"SELECT" in full_diff or "f'SELECT" in full_diff:
            error_rate = max(error_rate, 5.0)
            details.append("CWE-89: SQL injection via f-string interpolation in query construction.")
            severity_signals.append(0.85)

        # Check 8: Unpooled HTTP client / connection recreation in request handler
        if re.search(r"\b(HTTPAdapter\(|requests\.Session\(\))", full_diff) and "def " in full_diff and "global" not in full_diff:
            error_rate = 28.0
            p95 = sla_ms * 2.2
            details.append("Socket descriptor exhaustion: instantiated unpooled HTTP sessions inside request handlers.")
            severity_signals.append(0.70)

        # Check 9: CPU-bound computation blocking async event loop
        if "async def" in full_diff and re.search(r"\b(pbkdf2_hmac|bcrypt|argon2)\b", full_diff) and "run_in_threadpool" not in full_diff and "to_thread" not in full_diff:
            p95 = max(2400.0, sla_ms * 8.0)
            throughput = target_rps * 0.15
            details.append("CPU starvation: heavy cryptographic hashing inside async route blocked the event loop.")
            severity_signals.append(0.78)

        # Check 10: N+1 query storm in ORM loop
        if "for " in full_diff and (".profile" in full_diff or ".author" in full_diff or ".objects.get" in full_diff) and "select_related" not in full_diff and "prefetch_related" not in full_diff:
            p95 = sla_ms * 3.0
            p99 = sla_ms * 6.0
            details.append("N+1 database query storm: lazy loading related entities inside iteration loop.")
            severity_signals.append(0.60)

        # Check 11: Unbounded external microservice call without timeout
        if re.search(r"\b(session\.get\(|session\.post\(|httpx\.get\()", full_diff) and "timeout" not in full_diff and "ClientTimeout" not in full_diff:
            p95 = sla_ms * 2.5
            error_rate = 15.0
            details.append("Cascading failure vulnerability: outbound HTTP call without client timeout ceiling.")
            severity_signals.append(0.65)

        sla_met = (p95 <= sla_ms) and (peak_memory_mb <= max_mem) and (error_rate < 1.0) and not deadlock

        composite_severity = max(severity_signals) if severity_signals else 0.0

        if len(severity_signals) > 1:
            avg_secondary = sum(sorted(severity_signals)[:-1]) / max(1, len(severity_signals) - 1)
            composite_severity = min(1.0, composite_severity + avg_secondary * 0.15)

        return LoadSimulationResult(
            concurrent_users=50,
            throughput_rps=throughput,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            error_rate_pct=error_rate,
            distributed_deadlock_detected=deadlock,
            memory_peak_mb=peak_memory_mb,
            sla_met=sla_met,
            severity_multiplier=round(composite_severity, 3),
            details=" | ".join(details) if details else "All concurrency SLAs and throughput targets met."
        )
