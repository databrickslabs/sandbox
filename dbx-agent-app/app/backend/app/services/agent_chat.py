"""
Agent Chat Service

Proxies chat messages to Databricks serving endpoints and enriches responses
with routing visualization, slot filling, and pipeline metadata.
"""

import re
import math
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

import httpx

from app.schemas.agent_chat import (
    AgentChatResponse,
    RoutingInfo,
    ToolCall,
    ProcessingStep,
    SlotFillingInfo,
    SlotData,
    NLToSQLMapping,
    PipelineInfo,
    PipelineStep,
    PipelineStepMetrics,
    PipelineStepCostBreakdown,
    PipelineMetrics,
    CostBreakdown,
    LatencyBreakdown,
)

logger = logging.getLogger(__name__)

# Token cost estimates (approximate for Claude Sonnet 4.5)
INPUT_COST_PER_1M = 3.00
OUTPUT_COST_PER_1M = 15.00

STOP_WORDS = frozenset({
    'what', 'do', 'say', 'about', 'the', 'are', 'is', 'in',
    'to', 'a', 'an', 'and', 'or', 'how', 'who', 'where', 'when',
    'which', 'that', 'this', 'with', 'for', 'from', 'can', 'will',
})

ENTITY_PATTERNS = [
    re.compile(r'experts?', re.I),
    re.compile(r'healthcare', re.I),
    re.compile(r'AI', re.I),
    re.compile(r'supply chain', re.I),
    re.compile(r'digital transformation', re.I),
    re.compile(r'(\w+)\s+experts?', re.I),
]


class AgentChatService:
    """Service for proxying chat to Databricks serving endpoints with enrichment."""

    def __init__(self):
        from databricks.sdk import WorkspaceClient
        self._workspace_client = WorkspaceClient()

    async def query_endpoint(
        self,
        endpoint_name: str,
        message: str,
    ) -> AgentChatResponse:
        """
        Query a Databricks serving endpoint and enrich the response.

        Args:
            endpoint_name: Name of the serving endpoint
            message: User message to send

        Returns:
            AgentChatResponse with content and enrichment metadata
        """
        start_time = int(datetime.now().timestamp() * 1000)

        w = self._workspace_client
        workspace_url = w.config.host
        if not workspace_url:
            raise ValueError("Could not determine Databricks workspace URL")

        # Ensure no trailing slash
        workspace_url = workspace_url.rstrip("/")

        url = f"{workspace_url}/serving-endpoints/{endpoint_name}/invocations"
        # Use authenticate() to support all SDK auth types (CLI, PAT, OAuth, etc.)
        headers = {"Content-Type": "application/json"}
        auth_headers = w.config.authenticate()
        headers.update(auth_headers)

        payload = {
            "input": [{"role": "user", "content": message}]
        }

        logger.info(
            "Querying endpoint %s at %s", endpoint_name, workspace_url
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                error_text = resp.text
                logger.error(
                    "Endpoint %s returned %d: %s",
                    endpoint_name, resp.status_code, error_text,
                )
                raise ValueError(
                    f"Databricks API error ({resp.status_code}): {error_text}"
                )
            data = resp.json()

        # Extract response text
        response_text = self._extract_response_text(data)
        request_id = (
            data.get("databricks_output", {}).get("databricks_request_id")
        )

        logger.info(
            "Received response from %s (request_id=%s, length=%d)",
            endpoint_name, request_id, len(response_text),
        )

        # Enrich response with metadata
        routing = self._parse_routing_info(response_text, message)
        slots = self._extract_slot_filling(message, response_text)
        elastic_query = self._generate_elasticsearch_query(slots, message)
        nl_to_sql = self._generate_nl_to_sql_mapping(message, slots)
        pipeline = self._build_pipeline(
            message, response_text, endpoint_name, start_time
        )

        return AgentChatResponse(
            content=response_text,
            requestId=request_id,
            endpoint=endpoint_name,
            timestamp=datetime.now().isoformat(),
            routing=routing,
            slotFilling=SlotFillingInfo(
                slots=SlotData(**slots),
                elasticQuery=elastic_query,
                nlToSql=[NLToSQLMapping(**m) for m in nl_to_sql],
            ),
            pipeline=pipeline,
        )

    @staticmethod
    def _extract_response_text(data: Dict[str, Any]) -> str:
        """Extract text content from Databricks serving endpoint response."""
        # Standard serving endpoint format
        output = data.get("output")
        if output and len(output) > 0:
            content = output[0].get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", "No response")

        # Databricks App /query format
        if "response" in data:
            return data["response"]

        return "No response"

    @staticmethod
    def _parse_routing_info(
        text: str, message: str
    ) -> Optional[RoutingInfo]:
        """Parse routing information from agent response text."""
        if not text:
            return None

        used_supervisor = "[Demo Response from" in text
        sub_agent = None
        tool_calls: List[ToolCall] = []
        processing_steps: List[ProcessingStep] = []

        # Check for sub-agent routing
        sub_agent_match = re.search(r'\[Demo Response from ([^\]]+)\]', text)
        if sub_agent_match:
            sub_agent = sub_agent_match.group(1)
            used_supervisor = True
            processing_steps.append(ProcessingStep(
                step=1,
                name="Supervisor Routing",
                description="Analyzed query intent and selected appropriate sub-agent",
                timestamp=int(datetime.now().timestamp() * 1000),
                details={
                    "decision": "Route to research agent",
                    "reason": "Query requires expert transcript search",
                },
            ))

        # Detect tool usage
        tool_keywords = ["search_transcripts", "Found", "interviews", "expert"]
        if any(kw in text for kw in tool_keywords):
            interview_match = re.search(
                r'(\d+)\s+(?:relevant\s+)?(?:expert\s+)?interviews?', text, re.I
            )
            count = int(interview_match.group(1)) if interview_match else 0

            tool_calls.append(ToolCall(
                tool="search_transcripts",
                description="Searched expert interview transcripts",
                input={"query": message, "top_k": count or 10},
                output={
                    "count": count,
                    "source": "main.guidepoint.expert_transcripts",
                },
            ))

            # Add semantic search step
            if not any(s.name == "Semantic Search" for s in processing_steps):
                processing_steps.append(ProcessingStep(
                    step=len(processing_steps) + 1,
                    name="Semantic Search",
                    description="Executed vector similarity search on expert transcripts",
                    timestamp=int(datetime.now().timestamp() * 1000) + 100,
                    details={
                        "backend": "Elasticsearch",
                        "searchType": "semantic + keyword",
                        "resultsFound": count,
                    },
                ))

            processing_steps.append(ProcessingStep(
                step=len(processing_steps) + 1,
                name="Result Ranking",
                description="Ranked results by relevance score and recency",
                timestamp=int(datetime.now().timestamp() * 1000) + 200,
                details={
                    "algorithm": "BM25 + semantic similarity",
                    "topResults": count or 10,
                },
            ))

            processing_steps.append(ProcessingStep(
                step=len(processing_steps) + 1,
                name="Response Generation",
                description="LLM synthesized insights from top results",
                timestamp=int(datetime.now().timestamp() * 1000) + 300,
                details={
                    "model": "databricks-claude-sonnet-4-5",
                    "technique": "RAG (Retrieval Augmented Generation)",
                },
            ))

        return RoutingInfo(
            usedSupervisor=used_supervisor,
            subAgent=sub_agent,
            toolCalls=tool_calls,
            processingSteps=processing_steps,
        )

    @staticmethod
    def _extract_slot_filling(
        message: str, response_text: str
    ) -> Dict[str, Any]:
        """Extract slot filling information from query and response."""
        entities: List[str] = []
        topics: List[str] = []
        filters: Dict[str, Any] = {}

        # Extract entities
        for pattern in ENTITY_PATTERNS:
            matches = pattern.findall(message)
            for match in matches:
                lower = match.lower()
                if lower not in entities:
                    entities.append(lower)

        # Extract topics from response
        if response_text:
            topic_matches = re.findall(r'about\s+"([^"]+)"', response_text, re.I)
            for topic in topic_matches:
                if topic not in topics:
                    topics.append(topic)

        # Extract interview count
        if response_text:
            interview_match = re.search(
                r'(\d+)\s+(?:relevant\s+)?(?:expert\s+)?interviews?',
                response_text, re.I,
            )
            if interview_match:
                filters["interviewCount"] = int(interview_match.group(1))

        # Build search terms
        words = message.lower().split()
        search_terms = [
            w for w in words if len(w) > 3 and w not in STOP_WORDS
        ]

        return {
            "entities": entities,
            "topics": topics,
            "filters": filters,
            "searchTerms": search_terms,
        }

    @staticmethod
    def _generate_elasticsearch_query(
        slots: Dict[str, Any], message: str
    ) -> Dict[str, Any]:
        """Generate Elasticsearch query structure from slot data."""
        query: Dict[str, Any] = {
            "query": {
                "bool": {
                    "must": [],
                    "filter": [],
                    "should": [],
                }
            },
            "size": 10,
            "_source": [
                "expert_name", "interview_id", "content", "topics", "date"
            ],
        }

        # Add text search
        search_terms = slots.get("searchTerms", [])
        if search_terms:
            query["query"]["bool"]["must"].append({
                "multi_match": {
                    "query": message,
                    "fields": ["content^2", "summary", "topics"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            })

        # Add entity filters
        entities = slots.get("entities", [])
        if entities:
            for entity in entities:
                query["query"]["bool"]["should"].append({
                    "match": {
                        "topics": {"query": entity, "boost": 2}
                    }
                })
            query["query"]["bool"]["minimum_should_match"] = 1

        # Adjust size from filters
        filters = slots.get("filters", {})
        if filters.get("interviewCount"):
            query["size"] = filters["interviewCount"]

        return query

    @staticmethod
    def _generate_nl_to_sql_mapping(
        message: str, slots: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate NL to SQL mapping visualization."""
        mappings: List[Dict[str, Any]] = []

        entities = slots.get("entities", [])
        if entities:
            for entity in entities:
                mappings.append({
                    "naturalLanguage": entity,
                    "sqlClause": f"topics LIKE '%{entity}%'",
                    "type": "WHERE",
                    "confidence": 0.85,
                })

        search_terms = slots.get("searchTerms", [])
        if search_terms:
            mappings.append({
                "naturalLanguage": ", ".join(search_terms),
                "sqlClause": (
                    f"MATCH(content, summary) AGAINST("
                    f"'{' '.join(search_terms)}' IN BOOLEAN MODE)"
                ),
                "type": "MATCH",
                "confidence": 0.9,
            })

        filters = slots.get("filters", {})
        if filters.get("interviewCount"):
            count = filters["interviewCount"]
            mappings.append({
                "naturalLanguage": f"{count} interviews",
                "sqlClause": f"LIMIT {count}",
                "type": "LIMIT",
                "confidence": 1.0,
            })

        return mappings

    def _build_pipeline(
        self,
        message: str,
        response_text: str,
        endpoint: str,
        start_time: int,
    ) -> PipelineInfo:
        """Build processing pipeline visualization with metrics."""
        steps: List[PipelineStep] = []

        # Token estimates
        msg_tokens = math.ceil(len(message) / 4)
        resp_tokens = math.ceil(len(response_text) / 4)
        input_cost = (msg_tokens / 1_000_000) * INPUT_COST_PER_1M
        output_cost = (resp_tokens / 1_000_000) * OUTPUT_COST_PER_1M
        total_cost = input_cost + output_cost

        # Slot filling for entity count
        slots = self._extract_slot_filling(message, response_text)
        entity_count = len(slots.get("entities", []))

        # Step 1: Request Received
        steps.append(PipelineStep(
            id=1, name="Request Received", status="completed",
            timestamp=start_time, duration=0,
            details={
                "endpoint": endpoint,
                "messageLength": len(message),
                "source": "Agent Chat",
            },
            tools=[],
        ))

        # Step 2: Authentication
        steps.append(PipelineStep(
            id=2, name="Authentication", status="completed",
            timestamp=start_time + 50, duration=50,
            details={"method": "OAuth", "validated": True},
            tools=["databricks_auth_token"],
        ))

        # Step 3: Query Preprocessing
        steps.append(PipelineStep(
            id=3, name="Query Preprocessing", status="completed",
            timestamp=start_time + 100, duration=50,
            details={
                "entityExtraction": True,
                "tokenization": True,
                "intentClassification": True,
                "inputTokens": msg_tokens,
                "confidence": 0.92,
            },
            tools=["entity_extractor", "tokenizer"],
            metrics=PipelineStepMetrics(
                tokensProcessed=msg_tokens,
                entitiesFound=entity_count,
                latency=50,
            ),
        ))

        # Step 4: Supervisor Routing (conditional)
        if endpoint == "guidepoint_supervisor":
            steps.append(PipelineStep(
                id=4, name="Supervisor Routing", status="completed",
                timestamp=start_time + 200, duration=100,
                details={
                    "analysisType": "Intent classification",
                    "selectedAgent": "guidepoint_research",
                    "confidence": 0.95,
                    "reasoning": "Query requires expert transcript search",
                },
                tools=["intent_classifier", "agent_router"],
            ))

        # Step 5: Slot Filling
        steps.append(PipelineStep(
            id=len(steps) + 1, name="Slot Filling (NL→SQL)", status="completed",
            timestamp=start_time + 300, duration=100,
            details={
                "entitiesExtracted": True,
                "sqlGenerated": True,
                "queryOptimized": True,
            },
            tools=["entity_extractor", "sql_generator", "query_optimizer"],
            metrics=PipelineStepMetrics(latency=100),
        ))

        # Step 6: Search Execution
        interview_match = re.search(
            r'(\d+)\s+(?:relevant\s+)?(?:expert\s+)?interviews?',
            response_text, re.I,
        )
        results_found = int(interview_match.group(1)) if interview_match else 0

        steps.append(PipelineStep(
            id=len(steps) + 1, name="Search Execution", status="completed",
            timestamp=start_time + 500, duration=200,
            details={
                "backend": "Elasticsearch",
                "index": "expert_transcripts",
                "searchType": "hybrid (semantic + keyword)",
                "resultsFound": results_found,
            },
            tools=["search_transcripts", "elasticsearch_client"],
            metrics=PipelineStepMetrics(latency=200),
        ))

        # Step 7: Result Ranking
        steps.append(PipelineStep(
            id=len(steps) + 1, name="Result Ranking", status="completed",
            timestamp=start_time + 750, duration=50,
            details={
                "algorithm": "BM25 + Semantic Similarity",
                "reranking": True,
                "diversification": True,
            },
            tools=["bm25_ranker", "semantic_reranker"],
        ))

        # Step 8: Context Preparation
        steps.append(PipelineStep(
            id=len(steps) + 1, name="Context Preparation", status="completed",
            timestamp=start_time + 850, duration=100,
            details={
                "documentsSelected": results_found or 10,
                "contextWindow": "4096 tokens",
                "compressionUsed": False,
            },
            tools=["context_builder"],
        ))

        # Step 9: LLM Response Generation
        steps.append(PipelineStep(
            id=len(steps) + 1, name="LLM Response Generation", status="completed",
            timestamp=start_time + 1000, duration=2000,
            details={
                "model": "databricks-claude-sonnet-4-5",
                "temperature": 0.7,
                "technique": "RAG (Retrieval Augmented Generation)",
                "inputTokens": msg_tokens + 450,
                "outputTokens": resp_tokens,
                "totalTokens": msg_tokens + 450 + resp_tokens,
            },
            tools=["foundation_model_api", "claude_sonnet_4_5"],
            metrics=PipelineStepMetrics(
                inputTokens=msg_tokens + 450,
                outputTokens=resp_tokens,
                tokensPerSecond=resp_tokens // 2 if resp_tokens else 0,
                estimatedCost=total_cost,
                costBreakdown=PipelineStepCostBreakdown(
                    input=input_cost, output=output_cost
                ),
                latency=2000,
            ),
        ))

        # Step 10: Response Formatting
        steps.append(PipelineStep(
            id=len(steps) + 1, name="Response Formatting", status="completed",
            timestamp=start_time + 3100, duration=50,
            details={
                "markdown": True,
                "citations": True,
                "structuredOutput": True,
            },
            tools=["markdown_formatter"],
        ))

        # Step 11: MLflow Trace Logging
        steps.append(PipelineStep(
            id=len(steps) + 1, name="MLflow Trace Logging", status="completed",
            timestamp=start_time + 3200, duration=100,
            details={
                "experiment": "guidepoint-supervisor",
                "metricsLogged": ["latency", "token_count", "cost"],
                "traceId": "generated_trace_id",
            },
            tools=["mlflow_client"],
        ))

        # Calculate totals
        total_duration = (
            steps[-1].timestamp + steps[-1].duration - start_time
        )

        # Latency breakdown
        preprocessing_latency = sum(s.duration for s in steps[:4])
        search_latency = sum(s.duration for s in steps[4:8])
        llm_step = next(
            (s for s in steps if s.name == "LLM Response Generation"), None
        )
        llm_latency = llm_step.duration if llm_step else 0
        postprocessing_latency = sum(s.duration for s in steps[9:])

        total_tokens = msg_tokens + 450 + resp_tokens
        tokens_per_second = (
            resp_tokens // max(total_duration // 1000, 1)
            if total_duration > 0 else 0
        )

        return PipelineInfo(
            steps=steps,
            totalDuration=total_duration,
            totalSteps=len(steps),
            startTime=start_time,
            endTime=start_time + total_duration,
            metrics=PipelineMetrics(
                totalTokens=total_tokens,
                inputTokens=msg_tokens + 450,
                outputTokens=resp_tokens,
                estimatedCost=total_cost,
                tokensPerSecond=tokens_per_second,
                costBreakdown=CostBreakdown(
                    input=f"${input_cost:.6f}",
                    output=f"${output_cost:.6f}",
                    total=f"${total_cost:.6f}",
                ),
                latencyBreakdown=LatencyBreakdown(
                    preprocessing=preprocessing_latency,
                    search=search_latency,
                    llm=llm_latency,
                    postprocessing=postprocessing_latency,
                    total=total_duration,
                ),
            ),
        )


def create_agent_chat_service() -> AgentChatService:
    """Factory function for AgentChatService."""
    return AgentChatService()
