"""
SGP Research Assistant - Unity Catalog Native with MLflow Tracking

This version adds comprehensive performance tracking via MLflow:
- Tool execution latency per call
- Token usage and estimated costs
- UC Function performance metrics
- Error rates and types
- End-to-end agent performance

Key Value: Most organizations have ZERO visibility into agent performance.
This shows how Databricks makes agents observable out of the box.
"""

# IMPORTANT: Clean up auth environment BEFORE any Databricks SDK imports
# In Databricks Apps, both OAuth and PAT token are present in environment
# We must use OAuth-only to avoid "multiple auth methods" error
import os
if os.environ.get("DATABRICKS_CLIENT_ID"):  # Running in Databricks Apps
    # Remove PAT token to force OAuth usage
    os.environ.pop("DATABRICKS_TOKEN", None)

from uuid import uuid4
from typing import Generator, Dict, Any, Optional
import time
from contextlib import contextmanager
import contextlib

from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)
from databricks_langchain import ChatDatabricks
from databricks.sdk import WorkspaceClient
from databricks.sdk.config import Config
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
import mlflow


@contextlib.contextmanager
def _clean_environment():
    """
    Context manager to temporarily clean Databricks environment variables.
    This prevents SDK conflicts when creating clients with explicit credentials.

    Based on Kasal's authentication pattern for Databricks Apps.
    """
    old_env = {}
    env_vars_to_clean = [
        "DATABRICKS_TOKEN",
        "DATABRICKS_API_KEY",
        "DATABRICKS_CLIENT_ID",
        "DATABRICKS_CLIENT_SECRET",
        "DATABRICKS_CONFIG_FILE",
        "DATABRICKS_CONFIG_PROFILE"
    ]

    for var in env_vars_to_clean:
        if var in os.environ:
            old_env[var] = os.environ.pop(var)

    try:
        yield
    finally:
        # Restore environment variables
        os.environ.update(old_env)


class PerformanceMetrics:
    """
    Track performance metrics throughout agent execution.

    This provides the observability that most organizations lack.
    """

    def __init__(self):
        self.tool_calls: list[Dict[str, Any]] = []
        self.uc_function_latencies: list[float] = []
        self.total_tokens: int = 0
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.errors: list[Dict[str, str]] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def add_tool_call(self, tool_name: str, latency_ms: float, success: bool, result_size: int = 0):
        """Record a tool call with performance data."""
        self.tool_calls.append({
            "tool_name": tool_name,
            "latency_ms": latency_ms,
            "success": success,
            "result_size_bytes": result_size,
            "timestamp": time.time()
        })

    def add_uc_function_latency(self, latency_ms: float):
        """Track UC Function execution time separately."""
        self.uc_function_latencies.append(latency_ms)

    def add_error(self, error_type: str, error_message: str):
        """Track errors for reliability metrics."""
        self.errors.append({
            "type": error_type,
            "message": error_message,
            "timestamp": time.time()
        })

    def update_token_usage(self, prompt_tokens: int, completion_tokens: int):
        """Track token usage for cost estimation."""
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens = self.prompt_tokens + self.completion_tokens

    def get_summary(self) -> Dict[str, Any]:
        """Get summary metrics for logging."""
        total_latency = (self.end_time - self.start_time) * 1000 if self.end_time and self.start_time else 0

        return {
            # Overall performance
            "total_latency_ms": total_latency,
            "total_tool_calls": len(self.tool_calls),
            "successful_tool_calls": sum(1 for t in self.tool_calls if t["success"]),
            "failed_tool_calls": sum(1 for t in self.tool_calls if not t["success"]),

            # UC Function performance
            "uc_function_calls": len(self.uc_function_latencies),
            "avg_uc_function_latency_ms": sum(self.uc_function_latencies) / len(self.uc_function_latencies) if self.uc_function_latencies else 0,
            "max_uc_function_latency_ms": max(self.uc_function_latencies) if self.uc_function_latencies else 0,
            "min_uc_function_latency_ms": min(self.uc_function_latencies) if self.uc_function_latencies else 0,

            # Token usage and cost estimation
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost_usd": self._estimate_cost(),

            # Reliability
            "error_count": len(self.errors),
            "error_rate": len(self.errors) / max(len(self.tool_calls), 1),

            # Tool-specific metrics
            "tool_breakdown": self._get_tool_breakdown()
        }

    def _estimate_cost(self) -> float:
        """
        Estimate cost based on token usage.

        This is a huge value-add: automatic cost tracking per agent call.
        Most organizations have no idea what their agents cost.
        """
        # Example pricing for Claude Sonnet (adjust for actual model)
        # Input: $3/M tokens, Output: $15/M tokens
        input_cost = (self.prompt_tokens / 1_000_000) * 3.0
        output_cost = (self.completion_tokens / 1_000_000) * 15.0
        return round(input_cost + output_cost, 6)

    def _get_tool_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get per-tool metrics."""
        breakdown = {}
        for tool_call in self.tool_calls:
            tool_name = tool_call["tool_name"]
            if tool_name not in breakdown:
                breakdown[tool_name] = {
                    "call_count": 0,
                    "total_latency_ms": 0,
                    "success_count": 0,
                    "fail_count": 0
                }

            breakdown[tool_name]["call_count"] += 1
            breakdown[tool_name]["total_latency_ms"] += tool_call["latency_ms"]
            if tool_call["success"]:
                breakdown[tool_name]["success_count"] += 1
            else:
                breakdown[tool_name]["fail_count"] += 1

        # Calculate averages
        for tool_name in breakdown:
            tool_data = breakdown[tool_name]
            tool_data["avg_latency_ms"] = tool_data["total_latency_ms"] / tool_data["call_count"]
            tool_data["success_rate"] = tool_data["success_count"] / tool_data["call_count"]

        return breakdown


class SGPResearchAgentWithTracking(ResponsesAgent):
    """
    Research assistant with comprehensive MLflow performance tracking.

    Key Differentiator: Shows exactly what agents are doing:
    - How long each tool call takes
    - How much each query costs
    - Where bottlenecks are
    - Reliability metrics

    This is observability most organizations DON'T have.
    """

    def __init__(self, config=None):
        """Initialize agent with UC Function tools and MLflow tracking."""
        self.config = config or {}

        # UC configuration
        self.catalog = self.config.get("catalog", "main")
        self.schema = self.config.get("schema", "agents")

        # Workspace client for UC Function execution
        # Use Kasal's pattern: clean environment to prevent SDK conflicts
        import os

        # Capture credentials BEFORE cleaning environment
        workspace_url = os.environ.get("DATABRICKS_HOST", "https://fevm-serverless-dxukih.cloud.databricks.com")
        is_databricks_app = os.environ.get("DATABRICKS_CLIENT_ID") is not None
        client_id = os.environ.get("DATABRICKS_CLIENT_ID")
        client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET")
        token = os.environ.get("DATABRICKS_TOKEN")

        # Clean environment and create clients with explicit credentials
        # This prevents "more than one authorization method" errors
        with _clean_environment():
            if is_databricks_app:
                # In Databricks Apps: Use OAuth (client credentials)
                self.workspace = WorkspaceClient(
                    host=workspace_url,
                    client_id=client_id,
                    client_secret=client_secret
                )
            else:
                # Running locally: Use PAT token
                if token:
                    self.workspace = WorkspaceClient(
                        host=workspace_url,
                        token=token
                    )
                else:
                    # Fallback to default SDK authentication
                    self.workspace = WorkspaceClient()

            # Initialize Databricks Foundation Model (also needs clean env)
            self.llm = ChatDatabricks(
                endpoint=self.config.get("endpoint", "databricks-claude-sonnet-4-5"),
                temperature=self.config.get("temperature", 0.7),
                max_tokens=self.config.get("max_tokens", 4096),
            )

        # Performance tracking
        self.metrics = PerformanceMetrics()

        # Cache warehouse ID to avoid repeated lookups
        self._warehouse_id_cache = None

        # Create tools that call UC Functions
        self.tools = self._create_uc_tools()

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Build LangGraph workflow
        self.graph = self._create_graph()

    @contextmanager
    def _track_tool_execution(self, tool_name: str):
        """
        Context manager to track tool execution time and status.

        Usage:
            with self._track_tool_execution("search_transcripts"):
                result = execute_tool()
        """
        start_time = time.time()
        success = False
        result_size = 0

        try:
            yield  # Execute the tool
            success = True
        except Exception as e:
            self.metrics.add_error(type(e).__name__, str(e))
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.add_tool_call(tool_name, latency_ms, success, result_size)

            # Log to MLflow in real-time
            if mlflow.active_run():
                mlflow.log_metric(f"tool_{tool_name}_latency_ms", latency_ms)
                mlflow.log_metric(f"tool_{tool_name}_success", 1 if success else 0)

    def _execute_uc_function(self, statement: str, parameters: list = None) -> Any:
        """
        Execute UC Function with performance tracking.

        Key Insight: This is where we capture UC Function latency.
        Most organizations have no idea how long their data operations take.
        """
        start_time = time.time()

        try:
            result = self.workspace.statement_execution.execute_statement(
                warehouse_id=self._get_warehouse_id(),
                statement=statement,
                parameters=parameters or [],
                wait_timeout="30s"
            )

            # Track UC Function performance
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.add_uc_function_latency(latency_ms)

            # Log to MLflow
            if mlflow.active_run():
                mlflow.log_metric("uc_function_latency_ms", latency_ms)

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.add_uc_function_latency(latency_ms)
            self.metrics.add_error("UCFunctionError", str(e))

            if mlflow.active_run():
                mlflow.log_metric("uc_function_error", 1)

            raise

    def _create_uc_tools(self):
        """Create LangChain tools that wrap Unity Catalog Functions with tracking."""

        @tool
        def search_transcripts(query: str, top_k: int = 10) -> str:
            """
            Search expert interview transcripts for insights on a topic.

            This tool calls the Unity Catalog Function with full performance tracking.
            Every call is logged to MLflow with latency, success/failure, and cost.
            """
            with self._track_tool_execution("search_transcripts"):
                try:
                    # Use parameterized query to prevent SQL injection
                    statement = f"""
                        SELECT * FROM TABLE({self.catalog}.{self.schema}.search_transcripts(
                            query => :query,
                            top_k => :top_k
                        ))
                    """
                    parameters = [
                        {"name": "query", "value": query},
                        {"name": "top_k", "value": str(top_k)}
                    ]

                    # Execute with tracking
                    result = self._execute_uc_function(statement, parameters)

                    # Format results
                    formatted = self._format_search_results(result)

                    # Log result metadata
                    if mlflow.active_run():
                        mlflow.log_param("search_query", query[:100])  # Truncate for logging
                        mlflow.log_metric("search_results_count", len(result.result.data_array) if result.result and result.result.data_array else 0)

                    return formatted

                except Exception as e:
                    error_msg = f"Error searching transcripts: {str(e)}\n\nNote: Ensure UC Function '{self.catalog}.{self.schema}.search_transcripts' is registered and you have EXECUTE permissions."
                    return error_msg

        @tool
        def get_expert_profile(expert_id: str) -> str:
            """Get detailed profile information for a specific expert."""
            with self._track_tool_execution("get_expert_profile"):
                try:
                    statement = f"""
                        SELECT * FROM TABLE({self.catalog}.{self.schema}.get_expert_profile(
                            expert_id => :expert_id
                        ))
                    """
                    parameters = [{"name": "expert_id", "value": expert_id}]

                    result = self._execute_uc_function(statement, parameters)

                    formatted = self._format_expert_profile(result)

                    if mlflow.active_run():
                        mlflow.log_param("expert_id", expert_id)

                    return formatted

                except Exception as e:
                    return f"Error getting expert profile: {str(e)}"

        return [search_transcripts, get_expert_profile]

    def _get_warehouse_id(self) -> str:
        """Get SQL warehouse ID with caching."""
        if self._warehouse_id_cache:
            return self._warehouse_id_cache

        # Check config first
        if "warehouse_id" in self.config:
            self._warehouse_id_cache = self.config["warehouse_id"]
            return self._warehouse_id_cache

        # Use serverless warehouse if available (recommended)
        warehouses = self.workspace.warehouses.list()
        for warehouse in warehouses:
            if warehouse.enable_serverless_compute:
                self._warehouse_id_cache = warehouse.id
                return self._warehouse_id_cache

        # Fallback to first available warehouse
        first_warehouse = next(iter(warehouses), None)
        if first_warehouse:
            self._warehouse_id_cache = first_warehouse.id
            return self._warehouse_id_cache

        raise ValueError("No SQL warehouse available. Please configure warehouse_id.")

    def _format_search_results(self, result) -> str:
        """Format UC Function search results for agent consumption."""
        if not result.result or not result.result.data_array:
            return "No transcripts found matching your query."

        rows = result.result.data_array
        if len(rows) == 0:
            return "No transcripts found matching your query."

        # Build formatted response
        formatted = f"Found {len(rows)} relevant transcripts:\n\n"

        for i, row in enumerate(rows, 1):
            transcript_id = row[0]
            text = row[1]
            expert_id = row[2]
            expert_name = row[3]
            score = row[4]

            formatted += f"**{i}. {expert_name}** (Expert ID: {expert_id})\n"
            formatted += f"Relevance Score: {score:.2f}\n\n"

            if len(text) > 300:
                text = text[:300] + "..."
            formatted += f"{text}\n\n"
            formatted += f"_Transcript ID: {transcript_id}_\n\n"

        formatted += "\n---\n"
        formatted += f"Data source: Unity Catalog Function ({self.catalog}.{self.schema}.search_transcripts)\n"
        formatted += f"Powered by: Databricks Vector Search\n"

        return formatted

    def _format_expert_profile(self, result) -> str:
        """Format expert profile results."""
        if not result.result or not result.result.data_array:
            return "Expert profile not found."

        row = result.result.data_array[0]

        formatted = f"**Expert Profile**\n\n"
        formatted += f"Name: {row[1]}\n"
        formatted += f"ID: {row[0]}\n"
        formatted += f"Credentials: {row[2]}\n\n"
        formatted += f"**Bio:**\n{row[3]}\n\n"
        formatted += f"**Specialties:** {row[4]}\n"

        return formatted

    def _create_graph(self):
        """Build LangGraph state machine with tracking."""

        def agent_node(state: MessagesState):
            """Agent reasoning node with token usage tracking."""
            messages = state["messages"]

            system_msg = SystemMessage(content=f"""You are an expert research assistant with access to expert interview transcripts via Unity Catalog.

Your tools are Unity Catalog Functions registered in the {self.catalog}.{self.schema} schema:
- search_transcripts: Semantic search over transcripts using Vector Search
- get_expert_profile: Get detailed expert information

Performance tracking is enabled - every tool call is logged to MLflow with:
- Execution latency
- Token usage and costs
- Success/failure rates
- Result quality metrics

Your role:
- Search transcripts to find relevant expert opinions and insights
- Synthesize information across multiple interviews
- Cite specific experts with their credentials and IDs
- Provide balanced perspectives when experts disagree

When answering:
1. Use search_transcripts to find relevant information
2. Quote specific experts with their names and credentials
3. Reference expert IDs for traceability
4. Use get_expert_profile for detailed expert background
5. Summarize themes across multiple interviews
6. Be clear about confidence level in findings""")

            # Track LLM invocation
            start_time = time.time()
            response = self.llm_with_tools.invoke([system_msg] + messages)
            llm_latency_ms = (time.time() - start_time) * 1000

            # Extract token usage if available
            if hasattr(response, "response_metadata"):
                usage = response.response_metadata.get("usage", {})
                if usage:
                    self.metrics.update_token_usage(
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0)
                    )

            # Log LLM performance
            if mlflow.active_run():
                mlflow.log_metric("llm_latency_ms", llm_latency_ms)

            return {"messages": [response]}

        # Build graph
        workflow = StateGraph(MessagesState)
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", tools_condition)
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """Non-streaming prediction with comprehensive tracking."""
        # Start tracking
        self.metrics = PerformanceMetrics()  # Reset for this request
        self.metrics.start_time = time.time()

        # Start MLflow run
        with mlflow.start_run(nested=True):
            # Log request metadata
            mlflow.log_param("catalog", self.catalog)
            mlflow.log_param("schema", self.schema)
            mlflow.log_param("model_endpoint", self.config.get("endpoint"))

            # Convert request to LangChain messages
            messages = self.prep_msgs_for_llm([i.model_dump() for i in request.input])

            # Invoke graph
            result = self.graph.invoke({"messages": messages})

            # Extract final message
            final_message = result["messages"][-1]

            # End tracking
            self.metrics.end_time = time.time()

            # Log all metrics to MLflow
            summary = self.metrics.get_summary()
            for metric_name, metric_value in summary.items():
                if isinstance(metric_value, (int, float)):
                    mlflow.log_metric(metric_name, metric_value)
                elif isinstance(metric_value, dict):
                    # Log nested metrics (tool breakdown)
                    for sub_key, sub_value in metric_value.items():
                        if isinstance(sub_value, dict):
                            for subsub_key, subsub_value in sub_value.items():
                                if isinstance(subsub_value, (int, float)):
                                    mlflow.log_metric(f"{metric_name}_{sub_key}_{subsub_key}", subsub_value)

            # Log summary as artifact
            import json
            with open("/tmp/agent_metrics.json", "w") as f:
                json.dump(summary, f, indent=2)
            mlflow.log_artifact("/tmp/agent_metrics.json")

            # Create response
            output_item = self.create_text_output_item(
                text=final_message.content,
                id=str(uuid4())
            )

            return ResponsesAgentResponse(output=[output_item])

    def predict_stream(self, request: ResponsesAgentRequest) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """Streaming prediction with tracking."""
        # Start tracking
        self.metrics = PerformanceMetrics()
        self.metrics.start_time = time.time()

        # Start MLflow run
        with mlflow.start_run(nested=True):
            mlflow.log_param("catalog", self.catalog)
            mlflow.log_param("schema", self.schema)
            mlflow.log_param("streaming", True)

            # Convert request to LangChain messages
            messages = self.prep_msgs_for_llm([i.model_dump() for i in request.input])

            item_id = str(uuid4())
            aggregated_content = ""

            # Stream from graph
            for chunk in self.graph.stream({"messages": messages}, stream_mode="messages"):
                if hasattr(chunk[0], "content") and chunk[0].content:
                    delta = chunk[0].content
                    aggregated_content += delta
                    yield self.create_text_delta(delta=delta, item_id=item_id)

            # End tracking
            self.metrics.end_time = time.time()

            # Log metrics
            summary = self.metrics.get_summary()
            for metric_name, metric_value in summary.items():
                if isinstance(metric_value, (int, float)):
                    mlflow.log_metric(metric_name, metric_value)

            # Send final done event
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item=self.create_text_output_item(text=aggregated_content, id=item_id),
            )


# Example: How to use with MLflow tracking
if __name__ == "__main__":
    """
    Test the agent with MLflow tracking.

    This demonstrates the observability value-add:
    - Every metric logged automatically
    - Cost tracking per query
    - Performance bottleneck identification
    - Reliability monitoring
    """

    # Set MLflow experiment
    mlflow.set_experiment("/Users/your-name/agents-agent-tracking")

    # Create agent
    agent = SGPResearchAgentWithTracking({
        "catalog": "main",
        "schema": "agents",
        "endpoint": "databricks-claude-sonnet-4-5"
    })

    # Create test request
    from mlflow.types.responses import ResponsesAgentInputItem

    request = ResponsesAgentRequest(
        input=[
            ResponsesAgentInputItem(
                role="user",
                content="What do healthcare experts say about AI adoption? Find at least 3 experts."
            )
        ]
    )

    # Execute with tracking
    print("Testing agent with MLflow tracking...")
    print("=" * 60)

    response = agent.predict(request)

    print("\nAgent Response:")
    print("-" * 60)
    print(response.output[0].text)
    print("-" * 60)

    # Print performance summary
    print("\n📊 Performance Metrics:")
    print("-" * 60)
    summary = agent.metrics.get_summary()
    print(f"Total Latency: {summary['total_latency_ms']:.0f}ms")
    print(f"Tool Calls: {summary['total_tool_calls']}")
    print(f"UC Function Avg Latency: {summary['avg_uc_function_latency_ms']:.0f}ms")
    print(f"Total Tokens: {summary['total_tokens']:,}")
    print(f"Estimated Cost: ${summary['estimated_cost_usd']:.6f}")
    print(f"Error Rate: {summary['error_rate']:.2%}")
    print("\nTool Breakdown:")
    for tool_name, metrics in summary['tool_breakdown'].items():
        print(f"  {tool_name}:")
        print(f"    - Calls: {metrics['call_count']}")
        print(f"    - Avg Latency: {metrics['avg_latency_ms']:.0f}ms")
        print(f"    - Success Rate: {metrics['success_rate']:.2%}")
    print("-" * 60)

    print("\n✅ Check MLflow UI for detailed metrics and traces!")
    print(f"   Experiment: /Users/your-name/agents-agent-tracking")
