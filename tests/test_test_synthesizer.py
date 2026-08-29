"""Unit tests for DynamicTestSynthesizerAgent."""

from src.agents.test_synthesizer import DynamicTestSynthesizerAgent
from src.core.domain import ScenarioSpec, CandidateSubmission, NonFunctionalRequirements, FileChange


def test_test_synthesizer_detects_cache_drift():
    """Verify synthesizer generates cache coherence test when lru_cache is present."""
    agent = DynamicTestSynthesizerAgent()
    
    spec = ScenarioSpec(
        scenario_id="test-1",
        title="Test Cache",
        description="Testing cache",
        ground_truth_flaw="cache drift",
        expected_optimal_solution="redis cache"
    )
    
    submission = CandidateSubmission(
        candidate_id="cand-1",
        scenario_id="test-1",
        full_diff="+from functools import lru_cache\n+@lru_cache\ndef get(): pass"
    )
    
    tests = agent.synthesize_suite(submission, spec)
    assert len(tests) >= 1
    assert any(t.target_risk == "CONCURRENCY_STATE_DRIFT" for t in tests)
    assert any("test_multi_worker_cache_coherence" in t.test_name for t in tests)


def test_test_synthesizer_detects_deadlock_lock_acquisition():
    """Verify synthesizer generates deadlock test when lock is present."""
    agent = DynamicTestSynthesizerAgent()
    
    spec = ScenarioSpec(
        scenario_id="test-2",
        title="Test Lock",
        description="Testing lock",
        ground_truth_flaw="deadlock",
        expected_optimal_solution="ordered locks"
    )
    
    submission = CandidateSubmission(
        candidate_id="cand-2",
        scenario_id="test-2",
        full_diff="+async with lock_a:\n+    async with lock_b:\n+        pass"
    )
    
    tests = agent.synthesize_suite(submission, spec)
    assert len(tests) >= 1
    assert any(t.target_risk == "DISTRIBUTED_DEADLOCK" for t in tests)
