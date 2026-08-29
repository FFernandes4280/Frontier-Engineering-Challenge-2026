"""Automated pytest suite for FSM agent pipeline, tools and baseline."""

import pytest
import asyncio
from src.core.domain import ScenarioSpec, CandidateSubmission, FileChange
from src.tools.blast_radius import BlastRadiusAnalyzer
from src.tools.context_inspector import ContextInspector
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
    orchestrator = HolisticVettingOrchestrator(trace_dir="./traces")
    dossier, logger = await orchestrator.evaluate_submission(flawed_submission, sample_scenario)
    
    assert dossier.overall_vetting_score < 60.0
    assert dossier.recommendation.value in ["LEAN_NO", "REJECT"]
    assert len(dossier.evidence_citations) > 0
    assert logger.trajectory.total_duration_ms >= 0


@pytest.mark.asyncio
async def test_baseline_runner_execution(sample_scenario, flawed_submission):
    runner = BaselineVettingRunner(trace_dir="./traces")
    dossier, logger = await runner.evaluate_submission(flawed_submission, sample_scenario)
    
    assert dossier.overall_vetting_score >= 70.0  # Baseline is fooled by clean code
    assert logger.trajectory.total_duration_ms >= 0
