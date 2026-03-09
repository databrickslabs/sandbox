"""
Tests for the orchestrator service — planning, execution levels, JSON parsing.
"""

import json
import pytest
from app.services.orchestrator import (
    Orchestrator,
    SubTask,
    OrchestrationPlan,
    SubTaskResult,
    _parse_json_from_llm,
)


# ── _parse_json_from_llm ─────────────────────────────────────────────


class TestParseJsonFromLlm:
    """Tests for extracting JSON from LLM output."""

    def test_plain_json(self):
        raw = '{"complexity": "simple", "reasoning": "test"}'
        result = _parse_json_from_llm(raw)
        assert result["complexity"] == "simple"
        assert result["reasoning"] == "test"

    def test_json_with_markdown_fences(self):
        raw = '```json\n{"complexity": "complex", "reasoning": "multi-step"}\n```'
        result = _parse_json_from_llm(raw)
        assert result["complexity"] == "complex"

    def test_json_with_bare_fences(self):
        raw = '```\n{"key": "value"}\n```'
        result = _parse_json_from_llm(raw)
        assert result["key"] == "value"

    def test_json_with_whitespace(self):
        raw = '  \n  {"a": 1}  \n  '
        result = _parse_json_from_llm(raw)
        assert result["a"] == 1

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_from_llm("not json at all")

    def test_multiline_json_in_fences(self):
        raw = '```json\n{\n  "complexity": "simple",\n  "sub_tasks": []\n}\n```'
        result = _parse_json_from_llm(raw)
        assert result["complexity"] == "simple"
        assert result["sub_tasks"] == []


# ── _build_execution_levels ───────────────────────────────────────────


class TestBuildExecutionLevels:
    """Tests for DAG-based execution level grouping."""

    def test_empty_tasks(self):
        levels = Orchestrator._build_execution_levels([])
        assert levels == []

    def test_single_task_no_deps(self):
        tasks = [SubTask(description="task0", agent_id=1, agent_name="a")]
        levels = Orchestrator._build_execution_levels(tasks)
        assert levels == [[0]]

    def test_two_independent_tasks(self):
        tasks = [
            SubTask(description="task0", agent_id=1, agent_name="a"),
            SubTask(description="task1", agent_id=2, agent_name="b"),
        ]
        levels = Orchestrator._build_execution_levels(tasks)
        assert levels == [[0, 1]]

    def test_sequential_dependency(self):
        tasks = [
            SubTask(description="task0", agent_id=1, agent_name="a"),
            SubTask(description="task1", agent_id=2, agent_name="b", depends_on=[0]),
        ]
        levels = Orchestrator._build_execution_levels(tasks)
        assert levels == [[0], [1]]

    def test_diamond_dependency(self):
        """A depends on nothing, B and C depend on A, D depends on B and C."""
        tasks = [
            SubTask(description="A", agent_id=1, agent_name="a"),
            SubTask(description="B", agent_id=2, agent_name="b", depends_on=[0]),
            SubTask(description="C", agent_id=3, agent_name="c", depends_on=[0]),
            SubTask(description="D", agent_id=4, agent_name="d", depends_on=[1, 2]),
        ]
        levels = Orchestrator._build_execution_levels(tasks)
        assert len(levels) == 3
        assert levels[0] == [0]
        assert set(levels[1]) == {1, 2}
        assert levels[2] == [3]

    def test_out_of_range_dependency_ignored(self):
        """Dependencies pointing to invalid indices should not crash."""
        tasks = [
            SubTask(description="task0", agent_id=1, agent_name="a", depends_on=[99]),
        ]
        levels = Orchestrator._build_execution_levels(tasks)
        assert levels == [[0]]

    def test_three_levels(self):
        tasks = [
            SubTask(description="t0", agent_id=1, agent_name="a"),
            SubTask(description="t1", agent_id=2, agent_name="b", depends_on=[0]),
            SubTask(description="t2", agent_id=3, agent_name="c", depends_on=[1]),
        ]
        levels = Orchestrator._build_execution_levels(tasks)
        assert levels == [[0], [1], [2]]


# ── Plan parsing / fallback ──────────────────────────────────────────


class TestClassifyAndPlanParsing:
    """Tests for plan construction from parsed JSON (unit-level, no LLM call)."""

    def test_plan_from_valid_json(self):
        """Verify OrchestrationPlan construction from well-formed parsed data."""
        parsed = {
            "complexity": "complex",
            "reasoning": "needs two agents",
            "sub_tasks": [
                {"description": "search", "agent_id": 1, "agent_name": "search-agent", "depends_on": []},
                {"description": "summarize", "agent_id": 2, "agent_name": "summary-agent", "depends_on": [0]},
            ],
        }
        sub_tasks = [
            SubTask(
                description=st["description"],
                agent_id=st["agent_id"],
                agent_name=st["agent_name"],
                depends_on=st.get("depends_on", []),
            )
            for st in parsed["sub_tasks"]
        ]
        plan = OrchestrationPlan(
            complexity=parsed["complexity"],
            reasoning=parsed["reasoning"],
            sub_tasks=sub_tasks,
        )

        assert plan.complexity == "complex"
        assert len(plan.sub_tasks) == 2
        assert plan.sub_tasks[0].agent_name == "search-agent"
        assert plan.sub_tasks[1].depends_on == [0]

    def test_plan_missing_fields_defaults(self):
        """Sub-task with missing optional fields uses defaults."""
        parsed_st = {"description": "do something"}
        st = SubTask(
            description=parsed_st.get("description", "unknown"),
            agent_id=parsed_st.get("agent_id", 0),
            agent_name=parsed_st.get("agent_name", "unknown"),
            depends_on=parsed_st.get("depends_on", []),
        )
        assert st.agent_id == 0
        assert st.agent_name == "unknown"
        assert st.depends_on == []


# ── SubTaskResult ────────────────────────────────────────────────────


class TestSubTaskResult:
    """Tests for SubTaskResult dataclass."""

    def test_success_result(self):
        r = SubTaskResult(
            task_index=0,
            agent_id=1,
            agent_name="test",
            description="do thing",
            response="done",
            latency_ms=150,
            success=True,
        )
        assert r.success is True
        assert r.error is None

    def test_failure_result(self):
        r = SubTaskResult(
            task_index=0,
            agent_id=1,
            agent_name="test",
            description="do thing",
            response="",
            latency_ms=50,
            success=False,
            error="Connection refused",
        )
        assert r.success is False
        assert r.error == "Connection refused"
