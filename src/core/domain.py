"""Domain models for the Senior Software Engineering Vetting System."""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class RecommendationType(str, Enum):
    STRONG_HIRE = "STRONG_HIRE"
    HIRE = "HIRE"
    LEAN_NO = "LEAN_NO"
    REJECT = "REJECT"


class FindingSeverity(str, Enum):
    POSITIVE = "POSITIVE"
    MINOR_CONCERN = "MINOR_CONCERN"
    MAJOR_DEBT = "MAJOR_DEBT"
    CRITICAL_FLAW = "CRITICAL_FLAW"


class ArchitectureType(str, Enum):
    MICROSERVICES = "MICROSERVICES"
    MODULAR_MONOLITH = "MODULAR_MONOLITH"
    EVENT_DRIVEN = "EVENT_DRIVEN"
    DISTRIBUTED_API = "DISTRIBUTED_API"


class NonFunctionalRequirements(BaseModel):
    """SLA and production constraints for a scenario."""
    latency_p95_sla_ms: float = 100.0
    max_memory_mb: float = 256.0
    zero_downtime_required: bool = True
    concurrency_target_rps: int = 1000
    consistency_model: str = "Strong"  # Strong, Eventual, Read-After-Write


class ScenarioSpec(BaseModel):
    """Specification of the distributed engineering problem and codebase."""
    scenario_id: str
    title: str
    difficulty: str = "Senior"
    architecture_type: ArchitectureType = ArchitectureType.DISTRIBUTED_API
    description: str
    requirements: NonFunctionalRequirements = Field(default_factory=NonFunctionalRequirements)
    existing_codebase_map: Dict[str, str] = Field(
        default_factory=dict,
        description="File path to file summary/purpose in the existing repo"
    )
    ground_truth_flaw: str = Field(
        description="The real underlying issue (e.g., N+1 query, distributed lock order)"
    )
    expected_optimal_solution: str = Field(
        description="The architectural solution an elite senior is expected to apply"
    )


class FileChange(BaseModel):
    """Represents changes made to a single file."""
    path: str
    added_lines: int = 0
    deleted_lines: int = 0
    diff_content: str = ""
    is_new_file: bool = False


class CandidateSubmission(BaseModel):
    """Candidate's submitted solution and git history."""
    candidate_id: str
    scenario_id: str
    commit_messages: List[str] = Field(default_factory=list)
    file_changes: List[FileChange] = Field(default_factory=list)
    full_diff: str = ""
    explanation_notes: Optional[str] = None


class BlastRadiusMetrics(BaseModel):
    """Metrics evaluating how clean and focused the candidate's diff is."""
    files_modified_count: int = 0
    total_lines_changed: int = 0
    unnecessary_files_modified: List[str] = Field(default_factory=list)
    cyclomatic_complexity_delta: int = 0
    blast_radius_score: float = 1.0  # 1.0 = highly focused, <0.6 = noisy/unfocused


class ContextAlignmentMetrics(BaseModel):
    """Metrics assessing if the candidate respected existing codebase patterns."""
    reused_existing_utilities: bool = True
    ignored_existing_modules: List[str] = Field(default_factory=list)
    duplicated_logic_detected: bool = False
    api_contract_preserved: bool = True
    alignment_score: float = 1.0  # 0.0 to 1.0


class LoadSimulationResult(BaseModel):
    """Results of simulated or actual load test under concurrent load."""
    concurrent_users: int = 50
    throughput_rps: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    error_rate_pct: float = 0.0
    distributed_deadlock_detected: bool = False
    memory_peak_mb: float = 0.0
    sla_met: bool = True
    details: str = ""


class VerificationReport(BaseModel):
    """Comprehensive test and static analysis report."""
    functional_tests_passed: int = 0
    total_functional_tests: int = 0
    all_tests_passed: bool = True
    load_metrics: LoadSimulationResult = Field(default_factory=LoadSimulationResult)
    security_vulnerabilities_found: List[str] = Field(default_factory=list)
    static_analysis_clean: bool = True


class EvidenceCitation(BaseModel):
    """Specific line-by-line evidence cited in the vetting dossier."""
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    severity: FindingSeverity
    title: str
    explanation: str
    code_snippet: Optional[str] = None


class SeniorVettingDossier(BaseModel):
    """The final holistic evaluation report signed by the agent squad."""
    candidate_id: str
    scenario_id: str
    overall_vetting_score: float = Field(ge=0.0, le=100.0)  # 0 to 100
    recommendation: RecommendationType
    architecture_score: float = Field(ge=0.0, le=100.0)
    concurrency_scalability_score: float = Field(ge=0.0, le=100.0)
    code_quality_reusability_score: float = Field(ge=0.0, le=100.0)
    executive_summary: str
    trade_off_analysis: str
    evidence_citations: List[EvidenceCitation] = Field(default_factory=list)
    primary_flaws_flagged: List[str] = Field(default_factory=list)
    human_in_the_loop_approval_needed: bool = False
