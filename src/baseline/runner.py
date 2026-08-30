"""Canonical Baseline Runner: Highly-Prompt-Engineered Monolithic LLM Evaluator."""

import os
import re
import uuid
import tiktoken

from rich.console import Console
from rich.panel import Panel

from src.core.domain import (
    CandidateSubmission,
    RecommendationType,
    ScenarioSpec,
    SeniorVettingDossier,
)
from src.core.llm import LLMClient
from src.tracing.logger import TraceLogger

console = Console()

BASELINE_SYSTEM_PROMPT = """You are a Principal Software Architect and Senior Technical Hiring Reviewer at a top-tier technology firm.
Your task is to conduct a rigorous, holistic architectural review of a candidate's submitted Git diff within an enterprise repository.

### EVALUATION CRITERIA & SCORING RUBRICS (0-100):
1. **Architecture & Scalability (40 pts):**
   - Does the change introduce distributed concurrency issues (e.g. in-memory state drift across worker processes, race conditions, or distributed deadlocks)?
   - Does it violate horizontal scalability requirements or async event loop non-blocking contracts?
2. **Concurrency, Memory & Reliability (30 pts):**
   - Does it cause memory exhaustion (e.g., loading unpaginated datasets into RAM via .all() instead of streaming)?
   - Are locks acquired in a consistent, deadlock-free hierarchy?
3. **AST Context Alignment & Reusability (20 pts):**
   - Did the candidate reuse existing modules in the codebase AST map, or did they duplicate logic (violating DRY)?
   - Are public API contracts and response schemas preserved without breaking backwards compatibility?
4. **Code Quality & Security (10 pts):**
   - Clean syntax, proper error handling, zero SQL injection or OWASP vulnerabilities.

### CHAIN OF THOUGHT INSTRUCTIONS:
Step 1: Carefully analyze the Problem Specification and Codebase AST Map.
Step 2: Inspect the Git Diff for subtle distributed systems flaws, memory leaks, and lock contention under high concurrency.
Step 3: Calculate the score deduction for any identified architectural flaw.
Step 4: Output your final evaluation strictly following the format below.

### REQUIRED OUTPUT FORMAT:
Score: <Final integer score from 0 to 100>
Recommendation: <STRONG_HIRE | HIRE | LEAN_NO | REJECT>
Summary: <A detailed, 2-3 sentence technical justification citing the exact architectural trade-offs, potential runtime failures, and reasoning for the score.>
"""


class BaselineVettingRunner:
    """Baseline solution evaluating code diffs using advanced prompt engineering without dynamic execution."""

    def __init__(self, model: str = None, trace_dir: str = "./trajectories", verbose: bool = False):
        self.model = model or os.getenv("BASELINE_MODEL", "groq/openai/gpt-oss-120b")
        self.llm_client = LLMClient(default_model=self.model)
        self.trace_dir = trace_dir
        self.verbose = verbose

    async def evaluate_submission(
        self,
        submission: CandidateSubmission,
        spec: ScenarioSpec
    ) -> tuple[SeniorVettingDossier, TraceLogger]:
        """Evaluates the submission using a real LLM call with top-tier prompt engineering."""
        run_id = str(uuid.uuid4())[:8]
        logger = TraceLogger(
            run_id=run_id,
            runner_type="baseline",
            task_id=f"{spec.scenario_id}_{submission.candidate_id}",
            trace_dir=self.trace_dir
        )

        if self.verbose:
            console.print(Panel(f"[bold cyan]🔍 BASELINE STEP-BY-STEP EXECUTION TRACE[/bold cyan]\nTarget: [bold]{spec.title}[/bold] ({spec.github_repo or 'Local'})\nModel: [bold green]{self.model}[/bold green]", border_style="cyan"))

        # Step 1: Format AST Map summary and Diff
        ast_summary = "\n".join([f"- {path}: {desc}" for path, desc in spec.existing_codebase_map.items()]) if spec.existing_codebase_map else "No AST map available."
        diff_text = submission.full_diff or "\n".join([fc.diff_content for fc in submission.file_changes if fc.diff_content])

        user_content = (
            f"=== SCENARIO SPECIFICATION ===\n"
            f"Title: {spec.title}\n"
            f"Repository: {spec.github_repo or 'N/A'}\n"
            f"Architecture Topology: {spec.architecture_type.value}\n"
            f"Problem Description:\n{spec.description}\n\n"
            f"=== CODEBASE AST MAP (EXISTING SYMBOLS & MODULES) ===\n"
            f"{ast_summary}\n\n"
            f"=== CANDIDATE SUBMISSION GIT DIFF ===\n"
            f"{diff_text}\n\n"
            f"=== FUNCTIONAL TESTS STATUS ===\n"
            f"Status: 10/10 Baseline Unit Tests Passed (Sequential Local Execution)."
        )

        try:
            encoding = tiktoken.encoding_for_model(self.model)
        except Exception:
            encoding = tiktoken.get_encoding("cl100k_base")
        
        system_tokens = len(encoding.encode(BASELINE_SYSTEM_PROMPT))
        user_tokens = len(encoding.encode(user_content))
        total_tokens = system_tokens + user_tokens

        if total_tokens > 7000:
            if self.verbose:
                console.print(f"[bold yellow]⚠️ WARNING: Payload token count ({total_tokens}) exceeds 7000. Truncating diff...[/bold yellow]")
            
            # Re-encode user_content as a whole and truncate it directly to ensure we stay under the limit.
            # We want total_tokens <= 7000 (giving a 1000 token buffer to prevent counting mismatches).
            max_user_tokens = 7000 - system_tokens
            user_tokens_encoded = encoding.encode(user_content)
            
            if len(user_tokens_encoded) > max_user_tokens:
                truncated_user = user_tokens_encoded[:max_user_tokens - 50] + encoding.encode("\n\n[...TRUNCATED DUE TO TOKEN LIMITS...]")
                user_content = encoding.decode(truncated_user)

        if self.verbose:
            console.print("\n[bold yellow]📍 STEP 1: PROMPT-ENGINEERED PAYLOAD CONSTRUCTED[/bold yellow]")
            console.print(Panel(f"[bold]System Prompt (With Chain-of-Thought & Senior Rubrics):[/bold]\n{BASELINE_SYSTEM_PROMPT.strip()}\n\n[bold]User Payload:[/bold]\n{user_content[:1500]}...\n[dim](diff truncated for display)[/dim]", border_style="yellow"))

        logger.log_step(
            event_type="LLM_CALL",
            agent_name="BaselineMonolithicReviewer",
            input_data={"prompt": user_content, "model": self.model}
        )

        if self.verbose:
            console.print(f"\n[bold yellow]📍 STEP 2: DISPATCHING INFERENCE TO LLM ({self.model})...[/bold yellow]")

        # Step 2: Invoke LLM
        res = await self.llm_client.acomplete(
            messages=[
                {"role": "system", "content": BASELINE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            model=self.model,
            temperature=0.2
        )

        if self.verbose:
            console.print(f"\n[bold yellow]📍 STEP 3: RAW LLM RESPONSE RECEIVED ({res.latency_ms:.1f}ms | {res.total_tokens} tokens)[/bold yellow]")
            console.print(Panel(res.content, title="Raw Model Output", border_style="green"))

        logger.log_step(
            event_type="LLM_CALL",
            agent_name="BaselineMonolithicReviewer",
            output_data={"content": res.content},
            tokens=res.total_tokens,
            cost_usd=res.cost_usd,
            latency_ms=res.latency_ms
        )

        # Step 3: Parse response
        score = 0.0
        recommendation = RecommendationType.LEAN_NO
        
        score_match = re.search(r"Score:\s*(\d+(?:\.\d+)?)", res.content)
        if score_match:
            score = float(score_match.group(1))

        if "STRONG_HIRE" in res.content:
            recommendation = RecommendationType.STRONG_HIRE
        elif "LEAN_NO" in res.content:
            recommendation = RecommendationType.LEAN_NO
        elif "REJECT" in res.content:
            recommendation = RecommendationType.REJECT
        elif "HIRE" in res.content:
            recommendation = RecommendationType.HIRE

        if self.verbose:
            console.print("\n[bold yellow]📍 STEP 4: PARSING VERDICT & METRICS[/bold yellow]")
            console.print(f"  • Extracted Score: [bold cyan]{score}/100[/bold cyan]")
            console.print(f"  • Extracted Recommendation: [bold magenta]{recommendation.value}[/bold magenta]")
            console.print(f"  • Total Tokens Consumed: [bold]{res.total_tokens}[/bold]")
            console.print(f"  • API Duration: [bold]{res.latency_ms:.2f}ms[/bold]")

        dossier = SeniorVettingDossier(
            candidate_id=submission.candidate_id,
            scenario_id=spec.scenario_id,
            overall_vetting_score=score,
            recommendation=recommendation,
            architecture_score=score,
            concurrency_scalability_score=score,
            code_quality_reusability_score=score,
            executive_summary=res.content,
            trade_off_analysis="Baseline prompt-engineered review with Chain-of-Thought (without dynamic load execution).",
            evaluator_mode="baseline",
            evidence_citations=[],
            primary_flaws_flagged=[]
        )

        logger.finalize(success=(score >= 70.0))
        
        if self.verbose:
            console.print(Panel(f"[bold green]✅ BASELINE EVALUATION COMPLETED[/bold green]\nFinal Score: {score} | Recommendation: {recommendation.value}", border_style="green"))

        return dossier, logger
