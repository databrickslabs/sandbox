"""
Orchestrator Service — multi-agent planning, execution, and evaluation.

Transforms a user message into an orchestration plan (simple or complex),
executes sub-tasks across agents in parallel where possible,
and evaluates the combined results for quality.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 1


# ── Data structures ──────────────────────────────────────────────────

@dataclass
class SubTask:
    description: str
    agent_id: int
    agent_name: str
    depends_on: List[int] = field(default_factory=list)  # indices into sub_tasks list


@dataclass
class OrchestrationPlan:
    complexity: str  # "simple" | "complex"
    reasoning: str
    sub_tasks: List[SubTask] = field(default_factory=list)


@dataclass
class SubTaskResult:
    task_index: int
    agent_id: int
    agent_name: str
    description: str
    response: str
    latency_ms: int
    success: bool
    error: Optional[str] = None


@dataclass
class OrchestrationResult:
    final_response: str
    quality_score: float  # 1-5
    needs_retry: bool
    retry_suggestions: Optional[str] = None


# ── Helper ────────────────────────────────────────────────────────────

def _get_llm_config():
    """Get Databricks LLM endpoint URL and auth headers."""
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    endpoint_url = f"{w.config.host}/serving-endpoints/{settings.llm_endpoint}/invocations"
    headers = {"Content-Type": "application/json"}
    headers.update(w.config.authenticate())
    return endpoint_url, headers


async def _llm_call(endpoint_url: str, headers: dict, messages: list, max_tokens: int = 4096) -> str:
    """Make a single LLM call and return the content string."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            endpoint_url,
            headers=headers,
            json={
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def _parse_json_from_llm(text: str) -> dict:
    """Extract the first JSON object from LLM output, handling markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Drop first and last fence lines
        json_lines = []
        inside = False
        for line in lines:
            if line.strip().startswith("```") and not inside:
                inside = True
                continue
            if line.strip().startswith("```") and inside:
                break
            if inside:
                json_lines.append(line)
        cleaned = "\n".join(json_lines)
    return json.loads(cleaned)


# ── Orchestrator class ────────────────────────────────────────────────

class Orchestrator:
    """Plans, executes, and evaluates multi-agent orchestrations."""

    async def classify_and_plan(
        self,
        message: str,
        available_agents: List[Dict[str, Any]],
    ) -> OrchestrationPlan:
        """Classify the query and produce an orchestration plan.

        Args:
            message: The user's natural-language query.
            available_agents: List of agent dicts (id, name, description, capabilities).

        Returns:
            OrchestrationPlan with complexity and sub-tasks.
        """
        endpoint_url, headers = _get_llm_config()

        agent_descriptions = "\n".join(
            f"- Agent ID {a['id']}: {a['name']} — {a.get('description', 'no description')} "
            f"[capabilities: {a.get('capabilities', 'general')}]"
            for a in available_agents
        )

        system_prompt = """You are an orchestration planner. Given a user query and a list of available agents,
decide whether the query is "simple" (one agent can handle it) or "complex" (needs multiple agents).

For complex queries, decompose into sub-tasks with agent assignments.

Respond with ONLY a JSON object (no markdown fencing, no explanation):
{
  "complexity": "simple" or "complex",
  "reasoning": "brief explanation of your decision",
  "sub_tasks": [
    {
      "description": "what this sub-task should accomplish",
      "agent_id": <int>,
      "agent_name": "<name>",
      "depends_on": []
    }
  ]
}

Rules:
- depends_on contains indices (0-based) of sub_tasks this task depends on.
- For simple queries, return exactly one sub-task.
- Only assign agents from the available list.
- Prefer parallel execution: minimize dependencies."""

        user_prompt = f"""Available agents:
{agent_descriptions}

User query: {message}"""

        raw = await _llm_call(endpoint_url, headers, [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])

        try:
            parsed = _parse_json_from_llm(raw)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse plan JSON, falling back to simple plan. Raw: %s", raw[:500])
            if available_agents:
                first = available_agents[0]
                return OrchestrationPlan(
                    complexity="simple",
                    reasoning="Failed to parse LLM plan; delegating to best-match agent.",
                    sub_tasks=[SubTask(
                        description=message,
                        agent_id=first["id"],
                        agent_name=first["name"],
                    )],
                )
            return OrchestrationPlan(complexity="simple", reasoning="No agents available.", sub_tasks=[])

        sub_tasks = []
        for st in parsed.get("sub_tasks", []):
            sub_tasks.append(SubTask(
                description=st.get("description", message),
                agent_id=st.get("agent_id", 0),
                agent_name=st.get("agent_name", "unknown"),
                depends_on=st.get("depends_on", []),
            ))

        return OrchestrationPlan(
            complexity=parsed.get("complexity", "simple"),
            reasoning=parsed.get("reasoning", ""),
            sub_tasks=sub_tasks,
        )

    async def execute_plan(
        self,
        plan: OrchestrationPlan,
        base_url: str,
    ) -> List[SubTaskResult]:
        """Execute all sub-tasks, respecting dependency order.

        Tasks are grouped into levels: level 0 has no deps, level 1 depends
        only on level-0 tasks, etc. Tasks within a level run concurrently.
        """
        from app.routes.supervisor_runtime import _delegate_to_agent

        results: List[Optional[SubTaskResult]] = [None] * len(plan.sub_tasks)
        completed_indices: set = set()

        # Build levels
        levels = self._build_execution_levels(plan.sub_tasks)

        for level in levels:
            coros = []
            for idx in level:
                st = plan.sub_tasks[idx]
                coros.append(self._execute_single(idx, st, base_url, _delegate_to_agent))

            level_results = await asyncio.gather(*coros, return_exceptions=True)
            for i, res in enumerate(level_results):
                idx = level[i]
                if isinstance(res, Exception):
                    results[idx] = SubTaskResult(
                        task_index=idx,
                        agent_id=plan.sub_tasks[idx].agent_id,
                        agent_name=plan.sub_tasks[idx].agent_name,
                        description=plan.sub_tasks[idx].description,
                        response="",
                        latency_ms=0,
                        success=False,
                        error=str(res),
                    )
                else:
                    results[idx] = res
                completed_indices.add(idx)

        return [r for r in results if r is not None]

    async def evaluate_results(
        self,
        message: str,
        plan: OrchestrationPlan,
        results: List[SubTaskResult],
    ) -> OrchestrationResult:
        """Evaluate whether the combined results adequately answer the query."""
        endpoint_url, headers = _get_llm_config()

        results_summary = "\n\n".join(
            f"Sub-task {r.task_index} ({r.agent_name}): {'SUCCESS' if r.success else 'FAILED'}\n"
            f"Task: {r.description}\n"
            f"Response: {r.response[:1000]}"
            for r in results
        )

        system_prompt = """You are an evaluation agent. Given the original user query and sub-task results,
do TWO things:

1. Synthesize a clear, helpful final response for the user that combines all sub-task results.
2. Rate the overall quality.

Respond with ONLY a JSON object:
{
  "final_response": "The complete, user-facing answer synthesizing all results.",
  "quality_score": <float 1-5>,
  "needs_retry": <bool>,
  "retry_suggestions": "<optional string, only if needs_retry is true>"
}

A quality_score below 2.5 should set needs_retry to true."""

        user_prompt = f"""Original query: {message}

Plan reasoning: {plan.reasoning}

Sub-task results:
{results_summary}"""

        raw = await _llm_call(endpoint_url, headers, [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])

        try:
            parsed = _parse_json_from_llm(raw)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse evaluation JSON, using raw response.")
            return OrchestrationResult(
                final_response=raw or "Unable to synthesize results.",
                quality_score=3.0,
                needs_retry=False,
            )

        return OrchestrationResult(
            final_response=parsed.get("final_response", raw),
            quality_score=float(parsed.get("quality_score", 3.0)),
            needs_retry=bool(parsed.get("needs_retry", False)),
            retry_suggestions=parsed.get("retry_suggestions"),
        )

    # ── Internals ─────────────────────────────────────────────────────

    @staticmethod
    def _build_execution_levels(sub_tasks: List[SubTask]) -> List[List[int]]:
        """Group sub-task indices into execution levels by dependency depth."""
        n = len(sub_tasks)
        if n == 0:
            return []

        depth = [0] * n
        for i, st in enumerate(sub_tasks):
            for dep_idx in st.depends_on:
                if 0 <= dep_idx < n:
                    depth[i] = max(depth[i], depth[dep_idx] + 1)

        max_depth = max(depth) if depth else 0
        levels: List[List[int]] = [[] for _ in range(max_depth + 1)]
        for i, d in enumerate(depth):
            levels[d].append(i)
        return levels

    @staticmethod
    async def _execute_single(
        idx: int,
        sub_task: SubTask,
        base_url: str,
        delegate_fn,
    ) -> SubTaskResult:
        """Execute a single sub-task via A2A delegation."""
        start = time.monotonic()
        try:
            response = await delegate_fn(sub_task.agent_id, sub_task.description, base_url)
            elapsed = int((time.monotonic() - start) * 1000)
            is_error = response.startswith("Error:") or response.startswith("Delegation error:") or response.startswith("Delegation failed:")
            return SubTaskResult(
                task_index=idx,
                agent_id=sub_task.agent_id,
                agent_name=sub_task.agent_name,
                description=sub_task.description,
                response=response,
                latency_ms=elapsed,
                success=not is_error,
                error=response if is_error else None,
            )
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            return SubTaskResult(
                task_index=idx,
                agent_id=sub_task.agent_id,
                agent_name=sub_task.agent_name,
                description=sub_task.description,
                response="",
                latency_ms=elapsed,
                success=False,
                error=str(e),
            )
