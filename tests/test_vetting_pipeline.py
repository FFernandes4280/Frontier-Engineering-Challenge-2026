"""Automated pytest suite for FSM agent pipeline, tools and baseline."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from src.core.domain import ScenarioSpec, CandidateSubmission, FileChange
from src.core.llm import LLMResponse
from src.tools.blast_radius import BlastRadiusAnalyzer
from src.tools.load_simulator import LoadSimulator
from src.agents.orchestrator_fsm import HolisticVettingOrchestrator
from src.baseline.runner import BaselineVettingRunner


@pytest.fixture
def sample_scenario():
    return ScenarioSpec(
        scenario_id="test_01",
        title="Distributed Lock Test",
        description="Verify distributed lock acquisition order across services.",
        ground_truth_flaw="Deadlock under reversed lock acquisition.",
        expected_optimal_solution="Global lock hierarchy.",
        existing_codebase_map={"src/core/lock.py": "Redlock client"}
    )


@pytest.fixture
def flawed_submission():
    return CandidateSubmission(
        candidate_id="cand_flawed",
        scenario_id="test_01",
        full_diff="async with acquire_lock('lock_a'):\n async with acquire_lock('lock_b'):\n pass",
        file_changes=[
            FileChange(
                path="src/service.py",
                added_lines=3,
                deleted_lines=0,
                diff_content="async with acquire_lock('lock_a'):\n async with acquire_lock('lock_b'):"
            )
        ]
    )


def test_blast_radius_analyzer(sample_scenario, flawed_submission):
    metrics = BlastRadiusAnalyzer.analyze(flawed_submission, sample_scenario)
    assert metrics.files_modified_count == 1
    assert metrics.blast_radius_score > 0.8


def test_load_simulator_detects_deadlock(sample_scenario, flawed_submission):
    load_res = LoadSimulator.simulate(flawed_submission, sample_scenario)
    assert load_res.distributed_deadlock_detected is True
    assert load_res.sla_met is False


@pytest.mark.asyncio
async def test_fsm_orchestrator_execution(sample_scenario, flawed_submission):
    mock_llm_response = LLMResponse(
        content="Candidate failed due to distributed deadlocks.",
        model="groq/qwen/qwen3.8-27b",
        prompt_tokens=200,
        completion_tokens=50,
        total_tokens=250,
        cost_usd=0.0001,
        latency_ms=45.0
    )

    with patch("src.core.llm.LLMClient.acomplete", new_callable=AsyncMock, return_value=mock_llm_response):
        orchestrator = HolisticVettingOrchestrator(trace_dir="./traces")
        dossier, logger = await orchestrator.evaluate_submission(flawed_submission, sample_scenario)
        
        assert dossier.overall_vetting_score < 60.0
        assert dossier.recommendation.value in ["LEAN_NO", "REJECT"]
        assert len(dossier.evidence_citations) > 0


@pytest.mark.asyncio
async def test_baseline_runner_execution(sample_scenario, flawed_submission):
    mock_baseline_response = LLMResponse(
        content="Score: 88\nRecommendation: HIRE\nSummary: Clean code and tests passed.",
        model="groq/openai/gpt-oss-120b",
        prompt_tokens=150,
        completion_tokens=40,
        total_tokens=190,
        cost_usd=0.0008,
        latency_ms=120.0
    )

    with patch("src.core.llm.LLMClient.acomplete", new_callable=AsyncMock, return_value=mock_baseline_response):
        runner = BaselineVettingRunner(trace_dir="./traces")
        dossier, logger = await runner.evaluate_submission(flawed_submission, sample_scenario)
        
        assert dossier.overall_vetting_score == 88.0
        assert dossier.recommendation.value == "HIRE"
