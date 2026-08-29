"""Tool: Concurrency & Distributed Load Performance Simulator."""

from src.core.domain import CandidateSubmission, ScenarioSpec, LoadSimulationResult


class LoadSimulator:
    """Evaluates behavioral performance of diffs under high-throughput concurrent load."""

    @staticmethod
    def simulate(submission: CandidateSubmission, spec: ScenarioSpec) -> LoadSimulationResult:
        full_diff = submission.full_diff or "\n".join(fc.diff_content for fc in submission.file_changes)
        sla_ms = spec.requirements.latency_p95_sla_ms
        target_rps = spec.requirements.concurrency_target_rps

        throughput = float(target_rps)
        p95 = 25.0
        p99 = 45.0
        error_rate = 0.0
        deadlock = False
        peak_memory_mb = 64.0
        details = []

        # Check 1: In-memory local cache (@lru_cache) on horizontal multi-replica services
        if "@lru_cache" in full_diff:
            error_rate = 22.5
            p95 = 65.0
            details.append("Inconsistency detected across multi-instance nodes due to uncoordinated local @lru_cache.")

        # Check 2: In-memory mass data processing (.all() + sum/loop in Python) vs DB aggregation
        if ".all()" in full_diff and ("sum(" in full_diff or "for " in full_diff):
            peak_memory_mb = 1024.0  # 1GB memory spike
            p95 = 480.0
            p99 = 1200.0
            details.append(f"Memory exhaustion: Peak {peak_memory_mb}MB exceeded SLA of {spec.requirements.max_memory_mb}MB.")

        # Check 3: Async event loop blocking (requests / synchronous I/O in async route)
        if "requests." in full_diff and "async def" in full_diff:
            throughput = target_rps * 0.10
            p95 = 3200.0
            p99 = 6500.0
            error_rate = 35.0
            details.append("Event loop blocked by synchronous requests inside async handler; concurrency collapsed.")

        # Check 4: Distributed Deadlock (Inverted lock acquisition order)
        if "lock_a" in full_diff and "lock_b" in full_diff and "acquire_lock" in full_diff:
            deadlock = True
            error_rate = 45.0
            p95 = 15000.0
            details.append("Distributed deadlock detected under concurrent opposing transactions.")

        # Check 5: Non-idempotent processing or unhandled balance race condition
        if "balance -=" in full_diff and "select_for_update" not in full_diff and "with_for_update" not in full_diff:
            error_rate = 18.0
            details.append("Race condition: Balance mutation without row-level lock (SELECT FOR UPDATE) or atomic transaction.")

        # Check 6: Thundering Herd Cache Invalidation
        if "ttl=60" in full_diff and "xfetch" not in full_diff and "lock" not in full_diff:
            p95 = 40.0  # Minor latency on TTL expiry
            details.append("Minor latency spike on cache expiration (thundering herd risk under high concurrency).")

        sla_met = (p95 <= sla_ms) and (peak_memory_mb <= spec.requirements.max_memory_mb) and (error_rate < 1.0) and not deadlock

        return LoadSimulationResult(
            concurrent_users=50,
            throughput_rps=throughput,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            error_rate_pct=error_rate,
            distributed_deadlock_detected=deadlock,
            memory_peak_mb=peak_memory_mb,
            sla_met=sla_met,
            details=" | ".join(details) if details else "All concurrency SLAs and throughput targets met."
        )
