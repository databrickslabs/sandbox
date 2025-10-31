# MLflow GenAI for AI Agent Development

**Official Documentation**: 
- https://mlflow.org/docs/latest/api_reference/python_api/mlflow.genai.html
- https://docs.databricks.com/aws/en/mlflow3/genai/api-reference (Databricks-specific GenAI APIs)
- https://docs.databricks.com/aws/en/mlflow3/genai/ (Main MLflow GenAI concepts)

MLflow GenAI provides a comprehensive platform for building and managing generative AI applications on Databricks, with four key pillars: Tracing & Observability, Automated Quality Evaluation, Feedback & Continuous Improvement, and Application Lifecycle Management.

## Installation

Already included in this template:
```toml
# pyproject.toml
mlflow[databricks]>=3.1.1
```

## Setup

```python
import mlflow
import mlflow.genai

# Set tracking URI (automatic in Databricks)
mlflow.set_tracking_uri("databricks")
```

## 1. Tracing and Observability

### Trace Data Model

MLflow traces consist of two primary components:

**TraceInfo (Metadata):**
- Trace ID
- Request/response previews
- Execution duration
- State (OK, ERROR, IN_PROGRESS)
- Tags (key-value pairs for context)
- Assessments (feedback and expectations)

**TraceData (Core Payload):**
- `spans`: List of Span objects representing individual operations
- `request`: JSON-serialized input data
- `response`: JSON-serialized output data

**Span Types:**
- `CHAT_MODEL`: Interactions with chat models
- `TOOL`: Tool/function executions
- `AGENT`: Autonomous agent operations
- `RETRIEVER`: Document retrieval operations
- `PARSER`: Data parsing operations

**Documentation:**
- [Trace Data Model](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/data-model)

### Automatic Tracing

MLflow GenAI provides one-line instrumentation for capturing application execution across 20+ libraries:

```python
# Enable automatic tracing for popular libraries
mlflow.genai.autolog()

# Example with OpenAI
import openai
from openai import OpenAI

client = OpenAI(api_key="your-api-key")

# This will be automatically traced
response = client.chat.completions.create(
  model="gpt-4",
  messages=[{"role": "user", "content": "What is Databricks?"}],
  temperature=0.7
)
```

**Supported Libraries for Auto-tracing:**
- OpenAI
- LangChain
- Anthropic
- Hugging Face
- LlamaIndex
- And 15+ more

For the complete list of supported libraries, see: [Supported Libraries for Auto-instrumentation](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/auto-instrumentation.html)

### Manual Tracing

For custom applications or unsupported libraries, you can use custom tracing decorators and manual trace creation. See the [Manual Tracing Guide](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/manual-instrumentation.html) for detailed examples.

### Querying Traces

Search and analyze traces using the MLflow SDK:

```python
# Search traces across experiments
traces = mlflow.search_traces(
  experiment_ids=["exp1", "exp2"],
  filter_string="attributes.status = 'OK'",
  max_results=100,
  order_by=["attributes.timestamp_ms DESC"],
  return_type="pandas"  # or "list"
)

# Filter by timestamp
recent_traces = mlflow.search_traces(
  filter_string="attributes.timestamp_ms > 1640995200000",
  max_results=50
)

# Filter by tags
production_traces = mlflow.search_traces(
  filter_string="tags.environment = 'production'",
  order_by=["attributes.execution_time_ms ASC"]
)

# Filter by user
user_traces = mlflow.search_traces(
  filter_string="metadata.`mlflow.user` = 'alice@company.com'",
  max_results=25
)
```

### Getting Individual Traces

Retrieve detailed information about a specific trace:

```python
# Get a specific trace by ID
trace = mlflow.get_trace("tr-6b5e570b50ca15ec41d2f02574ed8605")

# Access trace metadata
print(f"Trace ID: {trace.info.trace_id}")
print(f"Status: {trace.info.status}")
print(f"Execution Time: {trace.info.execution_time_ms}ms")
print(f"Tags: {dict(trace.info.tags)}")

# Access trace data
print(f"Request: {trace.data.request}")
print(f"Response: {trace.data.response}")

# Iterate through spans
for span in trace.data.spans:
  print(f"Span: {span.name} ({span.span_type})")
  print(f"  Start: {span.start_time_ns}")
  print(f"  End: {span.end_time_ns}")
  print(f"  Inputs: {span.inputs}")
  print(f"  Outputs: {span.outputs}")
  
  # Access span attributes
  if span.attributes:
    print(f"  Attributes: {dict(span.attributes)}")
```

**Search Filter Operators:**
- `=`, `!=`: Equal/not equal
- `<`, `>`, `<=`, `>=`: Comparison operators
- `AND`: Combine conditions

### Logging Assessments on Traces

Log feedback and expectations to evaluate trace quality:

```python
# Log feedback on trace quality
mlflow.log_feedback(
  trace_id="trace-123",
  feedback={"helpfulness": 4, "accuracy": 5},
  source="human",
  rationale="Response was helpful and accurate"
)

# Log binary feedback
mlflow.log_feedback(
  trace_id="trace-456",
  feedback={"is_helpful": True},
  source="human"
)

# Log LLM judge feedback
mlflow.log_feedback(
  trace_id="trace-789",
  feedback={"safety_score": 0.95},
  source="llm",
  rationale="No harmful content detected"
)

# Log expectations for ground truth
mlflow.log_expectation(
  trace_id="trace-123",
  expectation={"expected_response": "Databricks is a unified analytics platform"},
  source="human"
)

# Log multiple acceptable answers
mlflow.log_expectation(
  trace_id="trace-456",
  expectation={
    "acceptable_responses": [
      "To create a cluster, go to Compute -> Create Cluster",
      "Navigate to the Compute section and click Create Cluster"
    ]
  },
  source="expert"
)
```

**Assessment Documentation:**
- [Log Assessment Guide](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/concepts/log-assessment)

**Tracing Documentation:**
- [MLflow Tracing Guide](https://docs.databricks.com/mlflow/tracking.html)
- [GenAI Tracing](https://docs.databricks.com/aws/en/mlflow3/genai/tracing.html)
- [Query Traces via SDK](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/observe-with-traces/query-via-sdk)

## 2. Automated Quality Evaluation

### Built-in Scorers

MLflow GenAI provides AI-powered metrics to assess GenAI application quality:

```python
from mlflow.genai.scorers import (
  Correctness,
  Safety,
  RelevanceToQuery,
  RetrievalGroundedness,
  Guidelines
)

# Evaluate model responses
evaluation_data = [
  {"question": "What is Databricks?", "answer": "Databricks is a unified analytics platform..."},
  {"question": "How to create a cluster?", "answer": "To create a cluster in Databricks..."}
]

results = mlflow.genai.evaluate(
  data=evaluation_data,
  scorers=[
    Correctness(),
    Safety(),
    RelevanceToQuery(),
    Guidelines(guidelines="Responses should be accurate and helpful")
  ]
)

print(results.metrics)
```

### Custom Scorers

```python
@mlflow.genai.scorer(name="databricks_expertise")
def databricks_expertise_scorer(predictions, targets):
  """Custom scorer for Databricks domain expertise"""
  scores = []
  for pred, target in zip(predictions, targets):
    # Your custom scoring logic
    score = calculate_databricks_expertise(pred, target)
    scores.append(score)
  return {"databricks_expertise": sum(scores) / len(scores)}

# Use custom scorer
results = mlflow.genai.evaluate(
  data=evaluation_data,
  scorers=[databricks_expertise_scorer]
)
```

**Available Built-in Scorers:**
- `Correctness` - Measures factual accuracy
- `Safety` - Detects harmful content
- `RelevanceToQuery` - Measures relevance to the question
- `RetrievalGroundedness` - Checks if response is grounded in retrieved context
- `RetrievalRelevance` - Measures relevance of retrieved documents
- `RetrievalSufficiency` - Checks if retrieved context is sufficient
- `Guidelines` - Evaluates adherence to custom guidelines
- `ExpectationsGuidelines` - Evaluates against specific expectations

**Evaluation Documentation:**
- [MLflow Evaluation Guide](https://docs.databricks.com/aws/en/mlflow3/genai/evaluation.html)

## 3. Feedback and Continuous Improvement

### Human Labeling Sessions

```python
# Create labeling session for expert review
labeling_session = mlflow.genai.create_labeling_session(
  name="customer_support_evaluation",
  assigned_users=["expert1@company.com", "expert2@company.com"],
  agent="customer_support_agent",
  description="Evaluate customer support responses for quality"
)

# Get labeling sessions
sessions = mlflow.genai.get_labeling_sessions()
for session in sessions:
  print(f"Session: {session.name}, Status: {session.status}")

# Get review app for UI-based labeling
review_app = mlflow.genai.get_review_app(experiment_id="your-experiment-id")
print(f"Review app URL: {review_app.url}")
```

### Collecting Production Feedback

```python
# Convert problematic traces into test cases
def convert_trace_to_test_case(trace_id):
  """Convert a production trace into a test case for evaluation"""
  # Your logic to extract trace data and create test case
  pass

# Example: FastAPI endpoint for feedback
from fastapi import APIRouter

router = APIRouter()

@router.post("/feedback")
async def collect_feedback(trace_id: str, feedback: dict):
  """Collect feedback on AI responses"""
  # Log feedback directly on the trace
  mlflow.log_feedback(
    trace_id=trace_id,
    feedback={"rating": feedback["rating"], "type": feedback["type"]},
    source="user"
  )
  
  # Convert to test case if negative feedback
  if feedback["rating"] < 3:
    convert_trace_to_test_case(trace_id)
  
  return {"status": "feedback_recorded"}
```

## 4. Application Lifecycle Management

### Prompt Registry

```python
# Register prompts for centralized management
mlflow.genai.register_prompt(
  name="customer_support_prompt",
  template="You are a helpful customer support agent. Question: {question}",
  commit_message="Initial customer support prompt",
  tags={"version": "1.0", "team": "support"}
)

# Load prompts
prompt = mlflow.genai.load_prompt(
  name="customer_support_prompt",
  version=1
)

# Use prompt with variables
formatted_prompt = prompt.format(question="How do I create a cluster?")
```

### Prompt Optimization

```python
# Optimize prompts automatically
optimized_prompt = mlflow.genai.optimize_prompt(
  prompt="Answer the question: {question}",
  examples=[
    {"question": "What is Databricks?", "expected_answer": "Databricks is..."},
    {"question": "How to create clusters?", "expected_answer": "To create..."}
  ],
  model="gpt-4"
)

print(f"Optimized prompt: {optimized_prompt.template}")
```
## 6. Integration with FastAPI

### Complete GenAI API Example

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import mlflow
import mlflow.genai

router = APIRouter()

class ChatRequest(BaseModel):
  message: str
  session_id: str

class ChatResponse(BaseModel):
  response: str
  trace_id: str
  evaluation_metrics: dict

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
  try:
    # Load prompt from registry
    prompt = mlflow.genai.load_prompt("customer_support_prompt")
    formatted_prompt = prompt.format(question=request.message)
    
    # Generate response (your AI logic here) - will be automatically traced
    response = generate_ai_response(formatted_prompt)
    
    # Evaluate response quality
    evaluation = mlflow.genai.evaluate(
      data=[{"question": request.message, "answer": response}],
      scorers=[
        mlflow.genai.scorers.Safety(),
        mlflow.genai.scorers.RelevanceToQuery()
      ]
    )
    
    # Get the trace ID from the automatic tracing
    # (In practice, you'd capture this from the tracing context)
    trace_id = "auto-generated-trace-id"
    
    return ChatResponse(
      response=response,
      trace_id=trace_id,
      evaluation_metrics=evaluation.metrics
    )
  
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

def generate_ai_response(prompt: str) -> str:
  """Your AI generation logic here"""
  # Example: OpenAI call (will be automatically traced)
  from openai import OpenAI
  client = OpenAI()
  
  response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7
  )
  
  return response.choices[0].message.content
```

## 7. Production Monitoring

### Scheduled Evaluation

```python
# Add scheduled scorer for continuous monitoring
mlflow.genai.add_scheduled_scorer(
  scorer=mlflow.genai.scorers.Safety(),
  schedule="0 0 * * *",  # Daily at midnight
  data_source="production_logs"
)

# List scheduled scorers
scheduled_scorers = mlflow.genai.list_scheduled_scorers()
for scorer in scheduled_scorers:
  print(f"Scorer: {scorer.name}, Schedule: {scorer.schedule}")
```

### Convert to Prediction Function

```python
# Convert model serving endpoint to prediction function
predict_fn = mlflow.genai.to_predict_fn("databricks-llama-2-70b-chat")

# Use in evaluation
results = mlflow.genai.evaluate(
  data=evaluation_data,
  predict_fn=predict_fn,
  scorers=[mlflow.genai.scorers.Correctness()]
)
```

## Best Practices

1. **Enable Auto-tracing**: Use `mlflow.genai.autolog()` for automatic observability
2. **Use Prompt Registry**: Centralize prompt management with versioning
3. **Continuous Evaluation**: Set up scheduled scorers for production monitoring
4. **Collect Feedback**: Implement feedback loops for continuous improvement
5. **Custom Scorers**: Create domain-specific evaluation metrics
6. **Dataset Management**: Use Unity Catalog for evaluation datasets
7. **Trace Everything**: Capture complete execution visibility including costs

## Resource Links

- **MLflow GenAI Documentation**: https://mlflow.org/docs/latest/api_reference/python_api/mlflow.genai.html
- **Databricks GenAI Guide**: https://docs.databricks.com/aws/en/mlflow3/genai/
- **GenAI API Reference**: https://docs.databricks.com/aws/en/mlflow3/genai/api-reference
- **Tracing Documentation**: https://docs.databricks.com/aws/en/mlflow3/genai/tracing.html
- **Evaluation Guide**: https://docs.databricks.com/aws/en/mlflow3/genai/evaluation.html
- **Prompt Registry**: https://docs.databricks.com/aws/en/mlflow3/genai/prompt-registry.html