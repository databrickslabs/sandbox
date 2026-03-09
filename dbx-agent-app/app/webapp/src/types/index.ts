export interface App {
  id: number
  name: string
  owner: string | null
  url: string | null
  tags: string | null
  manifest_url: string | null
}

export interface MCPServer {
  id: number
  app_id: number | null
  server_url: string
  kind: 'managed' | 'external' | 'custom'
  uc_connection: string | null
  scopes: string | null
}

export interface Tool {
  id: number
  mcp_server_id: number
  name: string
  description: string | null
  parameters: string | null
}

export interface Collection {
  id: number
  name: string
  description: string | null
}

export interface CollectionItem {
  id: number
  collection_id: number
  app_id?: number
  mcp_server_id?: number
  tool_id?: number
  app?: App
  server?: MCPServer
  tool?: Tool
}

export interface CollectionCreate {
  name: string
  description?: string
}

export interface Agent {
  id: number
  name: string
  description: string | null
  capabilities: string | null
  status: 'draft' | 'active' | 'inactive' | 'error'
  collection_id: number | null
  endpoint_url: string | null
  a2a_capabilities: string | null
  skills: string | null
  protocol_version: string | null
  system_prompt: string | null
  created_at: string | null
  updated_at: string | null
}

export interface AgentCreate {
  name: string
  description?: string
  capabilities?: string
  status?: string
  collection_id?: number
  endpoint_url?: string
  auth_token?: string
  a2a_capabilities?: string
  skills?: string
  protocol_version?: string
  system_prompt?: string
}

// --- A2A Protocol types ---

export interface A2ASkill {
  id: string
  name: string
  description: string | null
  tags: string[] | null
}

export interface A2ACapabilities {
  streaming: boolean
  pushNotifications: boolean
}

export interface A2AAgentCard {
  name: string
  description: string | null
  version: string | null
  protocolVersion: string
  url: string
  capabilities: A2ACapabilities
  skills: A2ASkill[]
  securitySchemes: Record<string, unknown> | null
  security: unknown[] | null
}

export interface A2AMessagePart {
  text?: string
  mediaType?: string
}

export interface A2AMessage {
  messageId: string
  role: 'user' | 'agent'
  parts: A2AMessagePart[]
  contextId?: string
}

export interface A2AArtifact {
  artifactId: string
  name?: string
  parts: A2AMessagePart[]
}

export interface A2ATaskStatus {
  state: string
  stateReason?: string
}

export interface A2ATask {
  id: string
  contextId: string | null
  status: A2ATaskStatus
  messages: A2AMessage[]
  artifacts: A2AArtifact[]
  metadata: Record<string, unknown> | null
}

// --- Catalog & Workspace Asset types ---

export interface CatalogAsset {
  id: number
  asset_type: 'table' | 'view' | 'function' | 'model' | 'volume'
  catalog: string
  schema_name: string
  name: string
  full_name: string
  owner: string | null
  comment: string | null
  columns_json: string | null
  tags_json: string | null
  properties_json: string | null
  data_source_format: string | null
  table_type: string | null
  row_count: number | null
  created_at: string | null
  updated_at: string | null
  last_indexed_at: string | null
}

export interface WorkspaceAsset {
  id: number
  asset_type: 'notebook' | 'job' | 'dashboard' | 'pipeline' | 'cluster' | 'experiment'
  workspace_host: string
  path: string
  name: string
  owner: string | null
  description: string | null
  language: string | null
  tags_json: string | null
  metadata_json: string | null
  content_preview: string | null
  resource_id: string | null
  created_at: string | null
  updated_at: string | null
  last_indexed_at: string | null
}

export interface CatalogCrawlResponse {
  status: string
  message: string
  catalogs_crawled: number
  schemas_crawled: number
  assets_discovered: number
  new_assets: number
  updated_assets: number
  errors: string[]
}

export interface WorkspaceCrawlResponse {
  status: string
  message: string
  assets_discovered: number
  new_assets: number
  updated_assets: number
  by_type: Record<string, number>
  errors: string[]
}

export interface DiscoverFilters {
  search: string
  tags: string[]
  owner: string
  type: 'app' | 'server' | 'tool' | 'table' | 'view' | 'function' | 'model' | 'volume' | 'notebook' | 'job' | 'dashboard' | 'pipeline' | 'cluster' | 'experiment' | 'all'
}

// --- Semantic Search types ---

export interface SearchResultItem {
  asset_type: string
  asset_id: number
  name: string
  description: string | null
  full_name: string | null
  path: string | null
  owner: string | null
  score: number
  match_type: 'semantic' | 'keyword' | 'hybrid'
  snippet: string | null
}

export interface SearchResponse {
  query: string
  total: number
  results: SearchResultItem[]
  search_mode: 'semantic' | 'keyword' | 'hybrid'
}

export interface EmbedStatusResponse {
  total_assets: number
  embedded_assets: number
  pending_assets: number
  embedding_model: string
  dimension: number
}

// --- Lineage / Knowledge Graph types ---

export interface LineageNode {
  asset_type: string
  asset_id: number
  name: string
  full_name?: string
  depth: number
}

export interface LineageEdge {
  source_type: string
  source_id: number
  target_type: string
  target_id: number
  relationship_type: string
}

export interface LineageResponse {
  root_type: string
  root_id: number
  root_name: string
  direction: string
  nodes: LineageNode[]
  edges: LineageEdge[]
}

export interface ImpactAnalysisResponse {
  root_type: string
  root_id: number
  root_name: string
  affected_assets: LineageNode[]
  total_affected: number
}

export interface AssetRelationship {
  id: number
  source_type: string
  source_id: number
  source_name: string | null
  target_type: string
  target_id: number
  target_name: string | null
  relationship_type: string
  metadata_json: string | null
  discovered_at: string | null
}

export interface LineageCrawlResponse {
  status: string
  message: string
  relationships_discovered: number
  new_relationships: number
  errors: string[]
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  trace_id?: string
}

export interface TraceEvent {
  id: string
  trace_id: string
  type: 'request.started' | 'tool.called' | 'tool.output' | 'response.delta' | 'response.done'
  timestamp: string
  data: Record<string, any>
}

export interface Span {
  id: string
  trace_id: string
  name: string
  start_time: number
  end_time: number
  attributes: Record<string, any>
  status: 'OK' | 'ERROR'
}

export interface ChatRequest {
  text: string
  server_urls: string[]
  collection_id?: number
  trace_id?: string
  conversation_id?: string
}

export interface ChatResponse {
  text: string
  trace_id: string
  conversation_id: string
}

// --- Orchestration types (supervisor-runtime) ---

export interface OrchestrationSubTaskResult {
  task_index: number
  agent_id: number
  agent_name: string
  description: string
  response: string
  latency_ms: number
  success: boolean
  error?: string | null
}

export interface OrchestrationPlan {
  complexity: 'simple' | 'complex'
  reasoning: string
  sub_tasks: Array<{
    description: string
    agent_id: number
    agent_name: string
    depends_on: number[]
  }>
}

export interface OrchestrationChatResponse {
  response: string
  conversation_id: string
  plan?: OrchestrationPlan | null
  sub_task_results?: OrchestrationSubTaskResult[] | null
  agents_used: number
  tools_discovered: number
  tools_called: number
  quality_score?: number | null
  mock: boolean
}

// --- Conversation types ---

export interface Conversation {
  id: string
  title: string
  user_email: string | null
  collection_id: number | null
  message_count: number
  created_at: string | null
  updated_at: string | null
}

export interface ConversationMessage {
  id: number
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  trace_id: string | null
  created_at: string | null
}

export interface ConversationDetail extends Conversation {
  messages: ConversationMessage[]
}

export interface TraceResponse {
  trace_id: string
  spans: Span[]
}

export interface SupervisorGenerateRequest {
  collection_id: number
  mode: 'code-first' | 'mas'
}

export interface SupervisorGenerateResponse {
  supervisor_url: string
  code?: string
}

// --- Agent Chat types ---

export interface AgentChatToolCall {
  tool: string
  description: string
  input?: Record<string, unknown>
  output?: Record<string, unknown>
}

export interface AgentChatProcessingStep {
  step: number
  name: string
  description: string
  timestamp: number
  details: Record<string, unknown>
}

export interface RoutingInfo {
  usedSupervisor: boolean
  subAgent: string | null
  toolCalls: AgentChatToolCall[]
  processingSteps?: AgentChatProcessingStep[]
}

export interface NLToSQLMapping {
  naturalLanguage: string
  sqlClause: string
  type: string
  confidence: number
}

export interface SlotData {
  entities: string[]
  topics: string[]
  filters: Record<string, unknown>
  searchTerms: string[]
}

export interface SlotFillingInfo {
  slots: SlotData
  elasticQuery: Record<string, unknown>
  nlToSql: NLToSQLMapping[]
}

export interface PipelineStepCostBreakdown {
  input: number
  output: number
}

export interface PipelineStepMetrics {
  tokensProcessed?: number
  entitiesFound?: number
  inputTokens?: number
  outputTokens?: number
  tokensPerSecond?: number
  estimatedCost?: number
  costBreakdown?: PipelineStepCostBreakdown
  latency?: number
}

export interface PipelineStep {
  id: number
  name: string
  status: string
  timestamp: number
  duration: number
  details: Record<string, unknown>
  tools: string[]
  metrics?: PipelineStepMetrics
}

export interface CostBreakdown {
  input: string
  output: string
  total: string
}

export interface LatencyBreakdown {
  preprocessing: number
  search: number
  llm: number
  postprocessing: number
  total: number
}

export interface PipelineMetrics {
  totalTokens: number
  inputTokens: number
  outputTokens: number
  estimatedCost: number
  tokensPerSecond: number
  costBreakdown: CostBreakdown
  latencyBreakdown: LatencyBreakdown
}

export interface PipelineInfo {
  steps: PipelineStep[]
  totalDuration: number
  totalSteps: number
  startTime: number
  endTime: number
  metrics?: PipelineMetrics
}

export interface AgentChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  endpoint?: string
  routing?: RoutingInfo
  slotFilling?: SlotFillingInfo
  pipeline?: PipelineInfo
}

export interface AgentChatEndpoint {
  name: string
  displayName: string
  description: string
  type: string
  endpointUrl?: string
}

export interface AgentChatResponse {
  content: string
  requestId?: string
  endpoint: string
  timestamp: string
  routing?: RoutingInfo
  slotFilling?: SlotFillingInfo
  pipeline?: PipelineInfo
}

export interface AgentChatEndpointsResponse {
  endpoints: AgentChatEndpoint[]
  count: number
}

// --- Workspace Profile types ---

// --- Audit Log types ---

export interface AuditLogEntry {
  id: number
  timestamp: string
  user_email: string
  action: string
  resource_type: string
  resource_id: string | null
  resource_name: string | null
  details: string | null
  ip_address: string | null
}

export interface WorkspaceProfile {
  name: string
  host: string | null
  auth_type: string | null
  is_account_profile: boolean
  auth_valid: boolean
  auth_error: string | null
  username: string | null
}

export interface WorkspaceProfilesResponse {
  profiles: WorkspaceProfile[]
  config_path: string
  total: number
  valid: number
}

// --- System Builder types ---

export interface WiringEdge {
  source_agent: string
  target_agent: string
  env_var: string
}

export interface SystemDefinition {
  id: string
  name: string
  description: string
  agents: string[]
  edges: WiringEdge[]
  uc_catalog: string
  uc_schema: string
  created_at: string
  updated_at: string
}

export interface SystemCreate {
  name: string
  description?: string
  agents?: string[]
  edges?: WiringEdge[]
  uc_catalog?: string
  uc_schema?: string
}

export interface DeployStepResult {
  agent: string
  action: string
  status: 'success' | 'failed' | 'skipped'
  detail: string
}

export interface DeployResult {
  system_id: string
  steps: DeployStepResult[]
  status: 'success' | 'partial' | 'failed'
}
