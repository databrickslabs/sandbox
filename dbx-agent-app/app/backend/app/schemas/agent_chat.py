"""
Agent Chat Schemas

Pydantic models for the Agent Chat feature that proxies queries
to Databricks serving endpoints and enriches responses with
routing, slot filling, and pipeline metadata.
"""

from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


# --- Request schemas ---

class AgentChatRequest(BaseModel):
    """Request to query a Databricks serving endpoint."""
    endpoint_name: str = Field(..., description="Name of the Databricks serving endpoint")
    message: str = Field(..., min_length=1, description="User message to send to the agent")


# --- Routing schemas ---

class ToolCall(BaseModel):
    """A tool invocation by an agent."""
    tool: str = Field(..., description="Name of the tool invoked")
    description: str = Field(..., description="Description of what the tool did")
    input: Optional[Dict[str, Any]] = Field(None, description="Input parameters passed to the tool")
    output: Optional[Dict[str, Any]] = Field(None, description="Output returned by the tool")


class ProcessingStep(BaseModel):
    """A processing step in the agent routing flow."""
    step: int = Field(..., description="Step number in the processing sequence")
    name: str = Field(..., description="Name of the processing step")
    description: str = Field(..., description="Description of what this step does")
    timestamp: int = Field(..., description="Timestamp in milliseconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional step details")


class RoutingInfo(BaseModel):
    """Agent routing information showing supervisor/sub-agent flow."""
    usedSupervisor: bool = Field(False, description="Whether a supervisor agent was used for routing")
    subAgent: Optional[str] = Field(None, description="Name of the sub-agent that was routed to")
    toolCalls: List[ToolCall] = Field(default_factory=list, description="List of tool invocations")
    processingSteps: List[ProcessingStep] = Field(default_factory=list, description="Processing steps taken")


# --- Slot filling schemas ---

class NLToSQLMapping(BaseModel):
    """A natural language to SQL clause mapping."""
    naturalLanguage: str = Field(..., description="The natural language phrase")
    sqlClause: str = Field(..., description="The corresponding SQL clause")
    type: str = Field(..., description="Type of SQL clause (WHERE, MATCH, LIMIT)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the mapping")


class SlotData(BaseModel):
    """Extracted slot filling data from the user query."""
    entities: List[str] = Field(default_factory=list, description="Detected entities")
    topics: List[str] = Field(default_factory=list, description="Detected topics")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Extracted filters")
    searchTerms: List[str] = Field(default_factory=list, description="Search terms extracted from query")


class SlotFillingInfo(BaseModel):
    """Complete slot filling information including query construction."""
    slots: SlotData = Field(default_factory=SlotData, description="Extracted slot data")
    elasticQuery: Dict[str, Any] = Field(default_factory=dict, description="Generated Elasticsearch query")
    nlToSql: List[NLToSQLMapping] = Field(default_factory=list, description="NL to SQL mappings")


# --- Pipeline schemas ---

class PipelineStepCostBreakdown(BaseModel):
    """Cost breakdown for a pipeline step."""
    input: float = Field(0.0, description="Input token cost")
    output: float = Field(0.0, description="Output token cost")


class PipelineStepMetrics(BaseModel):
    """Metrics for a single pipeline step."""
    tokensProcessed: Optional[int] = Field(None, description="Tokens processed in this step")
    entitiesFound: Optional[int] = Field(None, description="Number of entities found")
    inputTokens: Optional[int] = Field(None, description="Input tokens used")
    outputTokens: Optional[int] = Field(None, description="Output tokens generated")
    tokensPerSecond: Optional[int] = Field(None, description="Token generation speed")
    estimatedCost: Optional[float] = Field(None, description="Estimated cost for this step")
    costBreakdown: Optional[PipelineStepCostBreakdown] = Field(None, description="Cost breakdown")
    latency: Optional[int] = Field(None, description="Step latency in milliseconds")


class PipelineStep(BaseModel):
    """A step in the processing pipeline."""
    id: int = Field(..., description="Step ID")
    name: str = Field(..., description="Step name")
    status: str = Field("completed", description="Step status")
    timestamp: int = Field(..., description="Step timestamp in milliseconds")
    duration: int = Field(0, description="Step duration in milliseconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Step details")
    tools: List[str] = Field(default_factory=list, description="Tools used in this step")
    metrics: Optional[PipelineStepMetrics] = Field(None, description="Step metrics")


class CostBreakdown(BaseModel):
    """Overall cost breakdown with formatted strings."""
    input: str = Field(..., description="Input cost formatted as dollar amount")
    output: str = Field(..., description="Output cost formatted as dollar amount")
    total: str = Field(..., description="Total cost formatted as dollar amount")


class LatencyBreakdown(BaseModel):
    """Latency breakdown by processing phase."""
    preprocessing: int = Field(0, description="Preprocessing latency in ms")
    search: int = Field(0, description="Search latency in ms")
    llm: int = Field(0, description="LLM generation latency in ms")
    postprocessing: int = Field(0, description="Postprocessing latency in ms")
    total: int = Field(0, description="Total latency in ms")


class PipelineMetrics(BaseModel):
    """Aggregate metrics for the entire pipeline."""
    totalTokens: int = Field(0, description="Total tokens used")
    inputTokens: int = Field(0, description="Total input tokens")
    outputTokens: int = Field(0, description="Total output tokens")
    estimatedCost: float = Field(0.0, description="Total estimated cost")
    tokensPerSecond: int = Field(0, description="Overall token generation speed")
    costBreakdown: CostBreakdown = Field(..., description="Cost breakdown")
    latencyBreakdown: LatencyBreakdown = Field(..., description="Latency breakdown")


class PipelineInfo(BaseModel):
    """Complete processing pipeline information."""
    steps: List[PipelineStep] = Field(default_factory=list, description="Pipeline steps")
    totalDuration: int = Field(0, description="Total pipeline duration in ms")
    totalSteps: int = Field(0, description="Number of steps in pipeline")
    startTime: int = Field(0, description="Pipeline start time in ms")
    endTime: int = Field(0, description="Pipeline end time in ms")
    metrics: Optional[PipelineMetrics] = Field(None, description="Aggregate pipeline metrics")


# --- Response schemas ---

class AgentChatResponse(BaseModel):
    """Response from querying a Databricks serving endpoint."""
    content: str = Field(..., description="Response text from the agent")
    requestId: Optional[str] = Field(None, description="Databricks request ID for tracing")
    endpoint: str = Field(..., description="Name of the endpoint that was queried")
    timestamp: str = Field(..., description="ISO format timestamp of the response")
    routing: Optional[RoutingInfo] = Field(None, description="Agent routing information")
    slotFilling: Optional[SlotFillingInfo] = Field(None, description="Slot filling and query construction info")
    pipeline: Optional[PipelineInfo] = Field(None, description="Processing pipeline visualization data")


class AgentChatEndpoint(BaseModel):
    """An available agent chat endpoint."""
    name: str = Field(..., description="Endpoint name")
    displayName: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="Description of the endpoint")
    type: str = Field(..., description="Endpoint type (research, supervisor, etc.)")
    endpointUrl: Optional[str] = Field(None, description="Direct URL of the endpoint")


class AgentChatEndpointsResponse(BaseModel):
    """Response listing available agent chat endpoints."""
    endpoints: List[AgentChatEndpoint] = Field(..., description="List of available endpoints")
    count: int = Field(..., description="Total number of endpoints")
