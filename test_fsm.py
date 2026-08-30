import asyncio
from src.core.domain import ScenarioSpec, CandidateSubmission, FileChange
from src.agents.orchestrator_fsm import HolisticVettingOrchestrator
from unittest.mock import AsyncMock, patch

async def main():
    scenario = ScenarioSpec(
        scenario_id="test_01",
        title="Test",
        ground_truth_flaw="None",
        expected_optimal_solution="None",
        description="Test",
        existing_codebase_map={"src/core/lock.py": "Redlock client"}
    )
    submission = CandidateSubmission(
        candidate_id="cand",
        scenario_id="test_01",
        full_diff="diff",
        file_changes=[]
    )
    
    with patch("src.core.llm.LLMClient.acomplete", new_callable=AsyncMock) as mock_complete:
        from src.core.llm import LLMResponse
        mock_complete.return_value = LLMResponse(
            content="CalibratedScore: 40\nRecommendation: REJECT\nSummary: Failed",
            model="test",
            tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "read_module_code", "arguments": "{\"module_name\": \"src/core/lock.py\"}"}}]
        )
        orchestrator = HolisticVettingOrchestrator()
        try:
            dossier, logger = await orchestrator.evaluate_submission(submission, scenario)
            print("Success!", dossier)
        except Exception as e:
            print("Failed!", e)

asyncio.run(main())
