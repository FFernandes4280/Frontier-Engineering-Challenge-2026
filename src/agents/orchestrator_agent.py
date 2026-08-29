"""Agent 1: Scenario & Architecture Provisioner."""

from src.core.domain import ScenarioSpec


class ScenarioProvisionerAgent:
    """Provisions and structures the technical evaluation scenario context."""

    def __init__(self, name: str = "ScenarioProvisionerAgent"):
        self.name = name

    def provision_scenario(self, spec: ScenarioSpec) -> dict:
        """Packages the scenario requirements, architecture topology and SLAs."""
        return {
            "scenario_id": spec.scenario_id,
            "title": spec.title,
            "difficulty": spec.difficulty,
            "architecture_type": spec.architecture_type.value,
            "sla_p95_ms": spec.requirements.latency_p95_sla_ms,
            "max_memory_mb": spec.requirements.max_memory_mb,
            "consistency_model": spec.requirements.consistency_model,
            "existing_codebase_map": spec.existing_codebase_map
        }
