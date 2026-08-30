"""Dynamic Test Synthesizer Agent: Generates targeted concurrency & stress tests from diff and AST."""

from pydantic import BaseModel

from src.core.domain import CandidateSubmission, ScenarioSpec


class SynthesizedTest(BaseModel):
    """A dynamically generated test case targeting specific architectural risk."""
    test_id: str
    target_risk: str  # e.g., "CONCURRENCY_RACE", "MEMORY_EXHAUSTION", "DEADLOCK", "API_CONTRACT"
    test_name: str
    description: str
    synthetic_code: str
    concurrency_level: int = 50
    expected_sla_ms: float = 100.0


class DynamicTestSynthesizerAgent:
    """Agent that analyzes the candidate diff and codebase AST to synthesize stress test suites."""

    def __init__(self):
        self.name = "DynamicTestSynthesizerAgent"

    def synthesize_suite(self, submission: CandidateSubmission, spec: ScenarioSpec) -> list[SynthesizedTest]:
        """Synthesizes targeted dynamic tests based on the AST and diff patterns."""
        tests: list[SynthesizedTest] = []
        diff_lower = (submission.full_diff or "").lower()

        # 1. Concurrency / In-Memory State Drift Test
        if "lru_cache" in diff_lower or "cache" in diff_lower or "global" in diff_lower:
            tests.append(SynthesizedTest(
                test_id="TEST-CONC-01",
                target_risk="CONCURRENCY_STATE_DRIFT",
                test_name="test_multi_worker_cache_coherence",
                description="Simulates 8 worker processes issuing interleaved read/write mutations to verify state drift across replicas.",
                synthetic_code="""
async def test_cache_coherence_across_workers():
    # Spawns 8 async workers hitting separate process memory spaces
    tasks = [worker_session(i).get_user_profile(user_id=42) for i in range(8)]
    results = await asyncio.gather(*tasks)
    assert len(set(results)) == 1, "Cache drift detected across worker processes!"
""",
                concurrency_level=100,
                expected_sla_ms=50.0
            ))

        # 2. Memory Exhaustion / Streaming Test
        if ".all()" in diff_lower or "fetchall" in diff_lower or "stream" in diff_lower:
            tests.append(SynthesizedTest(
                test_id="TEST-MEM-01",
                target_risk="MEMORY_EXHAUSTION",
                test_name="test_high_volume_stream_memory_ceiling",
                description="Simulates streaming 1,000,000 rows to ensure process heap memory remains under 256MB.",
                synthetic_code="""
def test_stream_memory_footprint():
    tracemalloc.start()
    stream_records(count=1_000_000)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak / 1024 / 1024 < 256.0, f"Memory peak {peak/1024/1024:.1f}MB exceeded 256MB ceiling!"
""",
                concurrency_level=10,
                expected_sla_ms=200.0
            ))

        # 3. Distributed Deadlock Test
        if "acquire" in diff_lower or "lock" in diff_lower:
            tests.append(SynthesizedTest(
                test_id="TEST-LOCK-01",
                target_risk="DISTRIBUTED_DEADLOCK",
                test_name="test_cross_shard_opposing_lock_concurrency",
                description="Executes concurrent bidirectional transfers (A->B and B->A) to detect circular lock acquisition deadlocks.",
                synthetic_code="""
async def test_opposing_transfers_deadlock():
    # Dispatches opposing lock transfers simultaneously under high contention
    task1 = transfer_funds(account_a=1, account_b=2, amount=100)
    task2 = transfer_funds(account_a=2, account_b=1, amount=100)
    res1, res2 = await asyncio.wait_for(asyncio.gather(task1, task2), timeout=3.0)
    assert res1.status == 'SUCCESS' and res2.status == 'SUCCESS'
""",
                concurrency_level=50,
                expected_sla_ms=100.0
            ))

        # 4. Async Event Loop Blocking Test
        if "requests." in diff_lower or "time.sleep" in diff_lower:
            tests.append(SynthesizedTest(
                test_id="TEST-ASYNC-01",
                target_risk="EVENT_LOOP_STARVATION",
                test_name="test_event_loop_latency_under_concurrency",
                description="Measures event loop tick lag when concurrent I/O requests are executed.",
                synthetic_code="""
async def test_event_loop_responsiveness():
    start = time.perf_counter()
    await asyncio.gather(*[endpoint_handler() for _ in range(50)])
    elapsed = time.perf_counter() - start
    assert elapsed < 0.5, "Event loop blocked by synchronous blocking call!"
""",
                concurrency_level=50,
                expected_sla_ms=80.0
            ))

        # Default fallback test if no specific pattern is matched
        if not tests:
            tests.append(SynthesizedTest(
                test_id="TEST-GEN-01",
                target_risk="GENERAL_SLA_VERIFICATION",
                test_name="test_general_concurrency_and_contract_integrity",
                description="Executes synthetic high-throughput traffic load against modified public interfaces.",
                synthetic_code="""
async def test_load_and_contract_integrity():
    responses = await asyncio.gather(*[execute_endpoint() for _ in range(50)])
    assert all(r.status_code == 200 for r in responses)
""",
                concurrency_level=50,
                expected_sla_ms=100.0
            ))

        return tests
