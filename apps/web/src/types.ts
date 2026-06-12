export type HealthState = 'loading' | 'healthy' | 'error'

export type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

export type WorkspaceTab = 'command' | 'profile' | 'knowledge' | 'kernel' | 'intelligence' | 'settings'

export type Conversation = {
  id: string
  title: string
  updated_at: string
  message_count: number
}

export type MemoryEntry = {
  id: string
  content: string
  category: string
  source: string
  relevance?: number
}

export type DocumentEntry = {
  id: string
  title: string
  source: string
  tags: string[]
  chunk_count: number
}

export type CoreFeature = {
  id: string
  name: string
  status: string
  description: string
  capability_count: number
}

export type CapabilityEntry = {
  id: string
  name: string
  description: string
  category: string
  status: string
  permissions: string[]
  last_invoked_at?: string
}

export type CapabilityInvocationRecord = {
  id: string
  capability_name: string
  status: string
  dry_run: boolean
  created_at: string
}

export type AssistantProfile = {
  preferred_name?: string
  communication_style: string
  response_detail: string
  domains: string[]
  preferences: Record<string, unknown>
}

export type FeedbackSummary = {
  total: number
  by_rating: Record<string, number>
  by_category: Record<string, number>
}

export type WorkflowEntry = {
  id: string
  name: string
  trigger: string
  steps: string[]
  status: string
  last_run_at?: string
}

export type WorkflowRunRecord = {
  id: string
  workflow_name: string
  status: string
  dry_run: boolean
  created_at: string
}

export type DecisionEvaluation = {
  recommendation: string
  confidence_score: number
  risk_score: number
  cost_score: number
  impact_score: number
  rationale: string[]
  policy_verdict?: string
}

export type ReflectionResult = {
  summary: string
  issues: string[]
  improvements: string[]
  quality_score: number
  policy_verdict?: string
}

export type ConnectorEntry = {
  id: string
  provider: string
  status: string
  scopes: string[]
}

export type DigitalTwin = {
  preferred_name?: string | null
  domains: string[]
  inferred_work_style: string
  known_facts: Array<{ subject: string; relation: string; object: string; confidence: number }>
}

export type IntelligenceResult = {
  title: string
  details: string[]
}

export type ModuleSetting = {
  id: string
  name: string
  enabled: boolean
  category: string
  description: string
}

export type EnterpriseOverview = {
  posture: 'ready' | 'watch' | 'attention'
  readiness_score: number
  generated_at: string
  llm: {
    provider: string
    status: string
    model: string
  }
  metrics: Record<string, number>
  governance: {
    enabled_modules: number
    total_modules: number
    enabled_capabilities: number
    total_capabilities: number
    disabled_features: CoreFeature[]
  }
  risks: string[]
  next_actions: string[]
  recent_activity: Array<{
    label: string
    status: string
    created_at: string
    type: string
  }>
  recent_conversations: Conversation[]
}

export type UserPublic = {
  id: string
  email: string
  full_name?: string | null
  role: string
  created_at: string
}

export type AuthToken = {
  access_token: string
  token_type: string
  user: UserPublic
}

