import React, { useEffect, useRef, useState, type FormEvent } from 'react'
import { apiClient } from './api'
import { ChatWorkspace } from './components/ChatWorkspace'
import { normalizeMessages, updateMessage } from './messageUtils'
import type {
  AssistantProfile,
  AuthToken,
  CapabilityEntry,
  CapabilityInvocationRecord,
  ConnectorEntry,
  Conversation,
  DecisionEvaluation,
  DigitalTwin,
  DocumentEntry,
  EnterpriseOverview,
  FeedbackSummary,
  HealthState,
  IntelligenceResult,
  MemoryEntry,
  Message,
  ModuleSetting,
  ReflectionResult,
  UserPublic,
  WorkflowEntry,
  WorkflowRunRecord,
  WorkflowRunOutput,
  WorkspaceTab,
} from './types'

const DEFAULT_API_URL = ''
const API_URL = (import.meta.env.VITE_API_URL ?? DEFAULT_API_URL).replace(/\/$/, '')
const TOKEN_STORAGE_KEY = 'shivaai_access_token'

export default function App() {
  const messageListRef = useRef<HTMLDivElement | null>(null)
  const recognitionRef = useRef<any>(null)
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY) ?? '')
  const [user, setUser] = useState<UserPublic | null>(null)
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login')
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authName, setAuthName] = useState('')
  const [authRole, setAuthRole] = useState('user')
  const [authMessage, setAuthMessage] = useState('')
  const [adminUsers, setAdminUsers] = useState<UserPublic[]>([])
  const [health, setHealth] = useState<HealthState>('loading')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [memoryInput, setMemoryInput] = useState('')
  const [memoryQuery, setMemoryQuery] = useState('')
  const [memories, setMemories] = useState<MemoryEntry[]>([])
  const [documents, setDocuments] = useState<DocumentEntry[]>([])
  const [documentTitle, setDocumentTitle] = useState('')
  const [documentContent, setDocumentContent] = useState('')
  const [documentTags, setDocumentTags] = useState('')
  const [features, setFeatures] = useState<CoreFeature[]>([])
  const [capabilities, setCapabilities] = useState<CapabilityEntry[]>([])
  const [capabilityQuery, setCapabilityQuery] = useState('')
  const [capabilityName, setCapabilityName] = useState('')
  const [capabilityDescription, setCapabilityDescription] = useState('')
  const [invocations, setInvocations] = useState<CapabilityInvocationRecord[]>([])
  const [workflows, setWorkflows] = useState<WorkflowEntry[]>([])
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRunRecord[]>([])
  const [latestWorkflowRun, setLatestWorkflowRun] = useState<WorkflowRunRecord | null>(null)
  const [workflowName, setWorkflowName] = useState('')
  const [workflowSteps, setWorkflowSteps] = useState('')
  const [decisionText, setDecisionText] = useState('')
  const [decisionResult, setDecisionResult] = useState<DecisionEvaluation | null>(null)
  const [reflectionText, setReflectionText] = useState('')
  const [reflectionResult, setReflectionResult] = useState<ReflectionResult | null>(null)
  const [connectors, setConnectors] = useState<ConnectorEntry[]>([])
  const [connectorQuery, setConnectorQuery] = useState('release blockers')
  const [digitalTwin, setDigitalTwin] = useState<DigitalTwin | null>(null)
  const [worldFact, setWorldFact] = useState('Keerthi prefers implementation-first updates')
  const [evolutionGap, setEvolutionGap] = useState('Need a reusable project risk review capability')
  const [skillGraphObjective, setSkillGraphObjective] = useState('Plan, execute, and verify a feature')
  const [domainPrompt, setDomainPrompt] = useState('Dashboard screen shows an error chart')
  const [intelligenceResult, setIntelligenceResult] = useState<IntelligenceResult | null>(null)
  const [moduleSettings, setModuleSettings] = useState<ModuleSetting[]>([])
  const [enterpriseOverview, setEnterpriseOverview] = useState<EnterpriseOverview | null>(null)
  const [settingsMessage, setSettingsMessage] = useState('')
  const [feedbackStatus, setFeedbackStatus] = useState<Record<string, string>>({})
  const [feedbackSummary, setFeedbackSummary] = useState<FeedbackSummary>({
    total: 0,
    by_rating: {},
    by_category: {},
  })
  const [profile, setProfile] = useState<AssistantProfile>({
    communication_style: 'concise',
    response_detail: 'balanced',
    domains: [],
    preferences: {},
  })
  const [domainInput, setDomainInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [continuousVoice, setContinuousVoice] = useState(false)
  const [autoSpeak, setAutoSpeak] = useState(false)
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceTab>('command')
  const [voiceStatus, setVoiceStatus] = useState('')

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((response) => response.json())
      .then((payload) => setHealth(payload.status === 'healthy' ? 'healthy' : 'error'))
      .catch(() => setHealth('error'))
  }, [])

  useEffect(() => {
    loadConversations()
    loadMemories()
    loadDocuments()
    loadFeatures()
    loadCapabilities()
    loadInvocations()
    loadWorkflows()
    loadWorkflowRuns()
    loadConnectors()
    loadDigitalTwin()
    loadProfile()
    loadFeedbackSummary()
    loadModuleSettings()
    loadEnterpriseOverview()
  }, [])

  useEffect(() => {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token)
      loadCurrentUser(token)
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      setUser(null)
      setAdminUsers([])
    }
  }, [token])

  useEffect(() => {
    if (token && user?.role === 'admin') {
      loadAdminUsers(token)
    }
  }, [token, user?.role])

  useEffect(() => {
    const list = messageListRef.current
    if (!list) return

    requestAnimationFrame(() => {
      list.scrollTo({
        top: list.scrollHeight,
        behavior: isSending ? 'auto' : 'smooth',
      })
    })
  }, [messages, isSending])

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop?.()
      window.speechSynthesis?.cancel()
    }
  }, [])

  async function loadConversations() {
    try {
      const response = await fetch(`${API_URL}/api/v1/chat/sessions`)
      const payload = await response.json()

      // Gateway returns paginated object: { conversations, total, limit, offset, has_more }
      // Legacy/other implementations may return an array.
      if (Array.isArray(payload)) {
        setConversations(payload)
      } else if (payload && Array.isArray(payload.conversations)) {
        setConversations(payload.conversations)
      } else {
        setConversations([])
      }
    } catch {
      setConversations([])
    }
  }


  async function loadMemories(query = '') {
    try {
      const params = new URLSearchParams()
      if (query.trim()) params.set('query', query.trim())
      const response = await fetch(`${API_URL}/api/v1/memory?${params.toString()}`)
      const payload = await response.json()
      setMemories(payload)
    } catch {
      setMemories([])
    }
  }

  async function loadDocuments() {
    try {
      const response = await fetch(`${API_URL}/api/v1/documents?limit=6`)
      const payload = await response.json()
      setDocuments(payload)
    } catch {
      setDocuments([])
    }
  }

  async function loadFeatures() {
    try {
      const response = await fetch(`${API_URL}/api/v1/features`)
      const payload = await response.json()
      setFeatures(payload)
    } catch {
      setFeatures([])
    }
  }

  async function loadCapabilities(query = '') {
    try {
      const params = new URLSearchParams()
      if (query.trim()) params.set('query', query.trim())
      const response = await fetch(`${API_URL}/api/v1/capabilities?${params.toString()}`)
      const payload = await response.json()
      setCapabilities(payload)
    } catch {
      setCapabilities([])
    }
  }

  async function loadInvocations() {
    try {
      const response = await fetch(`${API_URL}/api/v1/capabilities/invocations?limit=8`)
      const payload = await response.json()
      setInvocations(payload)
    } catch {
      setInvocations([])
    }
  }

  async function loadWorkflows() {
    try {
      const response = await fetch(`${API_URL}/api/v1/workflows?limit=6`)
      const payload = await response.json()
      setWorkflows(payload)
    } catch {
      setWorkflows([])
    }
  }

  async function loadWorkflowRuns() {
    try {
      const response = await fetch(`${API_URL}/api/v1/workflows/runs?limit=6`)
      const payload = await response.json()
      setWorkflowRuns(payload)
    } catch {
      setWorkflowRuns([])
    }
  }

  async function loadConnectors() {
    try {
      const response = await fetch(`${API_URL}/api/v1/connectors`)
      const payload = await response.json()
      setConnectors(payload)
    } catch {
      setConnectors([])
    }
  }

  async function loadDigitalTwin() {
    try {
      const response = await fetch(`${API_URL}/api/v1/world/digital-twin`)
      const payload = await response.json()
      setDigitalTwin(payload)
    } catch {
      setDigitalTwin(null)
    }
  }

  async function loadProfile() {
    try {
      const response = await fetch(`${API_URL}/api/v1/profile`)
      const payload = await response.json()
      setProfile(payload)
      setDomainInput((payload.domains ?? []).join(', '))
    } catch {
      setProfile({
        communication_style: 'concise',
        response_detail: 'balanced',
        domains: [],
        preferences: {},
      })
    }
  }

  async function loadFeedbackSummary() {
    try {
      const response = await fetch(`${API_URL}/api/v1/feedback/summary`)
      const payload = await response.json()
      setFeedbackSummary(payload)
    } catch {
      setFeedbackSummary({ total: 0, by_rating: {}, by_category: {} })
    }
  }

  async function loadModuleSettings() {
    try {
      const response = await fetch(`${API_URL}/api/v1/settings/modules`)
      const payload = await response.json()
      setModuleSettings(payload)
    } catch {
      setModuleSettings([])
    }
  }

  async function loadEnterpriseOverview() {
    try {
      const response = await fetch(`${API_URL}/api/v1/enterprise/overview`)
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail ?? 'Unable to load enterprise overview')
      setEnterpriseOverview(payload)
    } catch {
      setEnterpriseOverview(null)
    }
  }

  function isModuleEnabled(moduleId: string) {
    return moduleSettings.find((setting) => setting.id === moduleId)?.enabled ?? true
  }

  async function updateModuleSetting(moduleId: string, enabled: boolean) {
    setSettingsMessage('')
    try {
      const response = await fetch(`${API_URL}/api/v1/settings/modules/${moduleId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail ?? 'Unable to update module')
      setModuleSettings((current) =>
        current.map((setting) => (setting.id === moduleId ? payload : setting)),
      )
      setSettingsMessage(`${payload.name} ${payload.enabled ? 'enabled' : 'disabled'}.`)
      loadFeatures()
      loadCapabilities(capabilityQuery)
      loadEnterpriseOverview()
    } catch (error) {
      setSettingsMessage(error instanceof Error ? error.message : 'Unable to update module')
    }
  }

  function authHeaders(currentToken = token): HeadersInit {
    return currentToken ? { Authorization: `Bearer ${currentToken}` } : {}
  }

  async function loadCurrentUser(currentToken = token) {
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/me`, {
        headers: authHeaders(currentToken),
      })
      if (!response.ok) throw new Error('Unable to load current user')
      const payload = await response.json()
      setUser(payload)
      setAuthMessage(`Signed in as ${payload.email}`)
    } catch {
      setToken('')
      setAuthMessage('Session expired. Sign in again.')
    }
  }

  async function loadAdminUsers(currentToken = token) {
    try {
      const response = await fetch(`${API_URL}/api/v1/admin/users?limit=8`, {
        headers: authHeaders(currentToken),
      })
      if (!response.ok) throw new Error('Unable to load users')
      const payload = await response.json()
      setAdminUsers(payload)
    } catch {
      setAdminUsers([])
    }
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthMessage('')
    const endpoint = authMode === 'signup' ? 'signup' : 'login'
    const body =
      authMode === 'signup'
        ? {
            email: authEmail.trim(),
            password: authPassword,
            full_name: authName.trim() || null,
            role: authRole,
          }
        : { email: authEmail.trim(), password: authPassword }

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Authentication failed')
      }

      const authPayload = payload as AuthToken
      setToken(authPayload.access_token)
      setUser(authPayload.user)
      setAuthPassword('')
      setAuthMessage(`Signed in as ${authPayload.user.email}`)
    } catch (error) {
      setAuthMessage(error instanceof Error ? error.message : 'Authentication failed')
    }
  }

  function logout() {
    setToken('')
    setAuthPassword('')
    setAuthMessage('Signed out.')
  }

  async function saveMemory() {
    const content = memoryInput.trim()
    if (!content) return

    const response = await fetch(`${API_URL}/api/v1/memory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, category: 'semantic', source: 'manual' }),
    })

    if (response.ok) {
      setMemoryInput('')
      loadMemories(memoryQuery)
      loadEnterpriseOverview()
    }
  }

  async function saveDocument() {
    const title = documentTitle.trim()
    const content = documentContent.trim()
    if (!title || !content) return

    const response = await fetch(`${API_URL}/api/v1/documents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        content,
        source: 'web-ui',
        tags: documentTags
          .split(',')
          .map((tag) => tag.trim())
          .filter(Boolean),
        add_to_memory: true,
      }),
    })

    if (response.ok) {
      setDocumentTitle('')
      setDocumentContent('')
      setDocumentTags('')
      loadDocuments()
      loadMemories(memoryQuery)
      loadEnterpriseOverview()
    }
  }

  async function searchMemory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    loadMemories(memoryQuery)
  }

  async function searchCapabilities(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    loadCapabilities(capabilityQuery)
  }

  async function saveCapability() {
    const name = capabilityName.trim()
    const description = capabilityDescription.trim()
    if (!name || !description) return

    const response = await fetch(`${API_URL}/api/v1/capabilities`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        description,
        category: 'custom',
        permissions: ['custom:invoke'],
        metadata: { core_feature: 'governance' },
      }),
    })

    if (response.ok) {
      setCapabilityName('')
      setCapabilityDescription('')
      loadCapabilities(capabilityQuery)
      loadFeatures()
      loadEnterpriseOverview()
    }
  }

  async function invokeCapability(id: string, dryRun: boolean) {
    const response = await fetch(`${API_URL}/api/v1/capabilities/${id}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dry_run: dryRun,
        input: { source: 'web-ui', objective: 'Review current ShivaAI Jarvis progress' },
      }),
    })

    if (response.ok) {
      loadCapabilities(capabilityQuery)
      loadInvocations()
      loadEnterpriseOverview()
    }
  }

  async function saveWorkflow() {
    const name = workflowName.trim()
    const steps = workflowSteps
      .split('\n')
      .map((step) => step.trim())
      .filter(Boolean)
    if (!name || steps.length === 0) return

    const response = await fetch(`${API_URL}/api/v1/workflows`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, trigger: 'manual', steps, metadata: { source: 'web-ui' } }),
    })

    if (response.ok) {
      setWorkflowName('')
      setWorkflowSteps('')
      loadWorkflows()
      loadFeatures()
      loadEnterpriseOverview()
    }
  }

  async function runWorkflow(id: string, dryRun: boolean) {
    const response = await fetch(`${API_URL}/api/v1/workflows/${id}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dry_run: dryRun, input: { source: 'web-ui' } }),
    })

    if (response.ok) {
      const run = (await response.json()) as WorkflowRunRecord
      setLatestWorkflowRun(run)
      loadWorkflows()
      loadWorkflowRuns()
      loadEnterpriseOverview()
    }
  }

  function workflowFinalResponse(output?: WorkflowRunOutput) {
    return output?.final_response || output?.merged_response?.final_response || ''
  }

  function workflowDomains(output?: WorkflowRunOutput) {
    return output?.domain_awareness?.domains || output?.merged_response?.domains || []
  }

  function workflowKnowledgeCount(output?: WorkflowRunOutput) {
    return output?.knowledge_used?.length || output?.merged_response?.knowledge_used?.length || 0
  }

  async function evaluateDecision() {
    const decision = decisionText.trim()
    if (!decision) return

    const response = await fetch(`${API_URL}/api/v1/decisions/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        decision,
        options: [decision],
        risks: [],
        expected_impact: 'High product clarity',
        estimated_effort: 'small',
      }),
    })

    if (response.ok) {
      setDecisionResult(await response.json())
    }
  }

  async function reviewReflection() {
    const content = reflectionText.trim()
    if (!content) return

    const response = await fetch(`${API_URL}/api/v1/reflection/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, criteria: ['clarity', 'verification', 'risk'] }),
    })

    if (response.ok) {
      setReflectionResult(await response.json())
    }
  }

  async function saveWorldFact() {
    const fact = worldFact.trim()
    if (!fact) return
    const [subject = 'Project', ...rest] = fact.split(' ')
    const response = await fetch(`${API_URL}/api/v1/world/facts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        subject,
        relation: 'notes',
        object: rest.join(' ') || fact,
        confidence: 85,
      }),
    })

    if (response.ok) {
      setWorldFact('')
      loadDigitalTwin()
      loadEnterpriseOverview()
    }
  }

  async function runConnectorSearch(connectorId: string) {
    const params = new URLSearchParams({ query: connectorQuery.trim() || 'recent activity' })
    const response = await fetch(`${API_URL}/api/v1/connectors/${connectorId}/search?${params}`)
    if (response.ok) {
      const payload = await response.json()
      setIntelligenceResult({
        title: `${connectorId} search`,
        details: payload.results.map((item: { title: string; summary: string }) => `${item.title}: ${item.summary}`),
      })
    }
  }

  async function syncConnector(connectorId: string) {
    const response = await fetch(`${API_URL}/api/v1/connectors/${connectorId}/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: connectorQuery, dry_run: false }),
    })
    if (response.ok) {
      const payload = await response.json()
      setIntelligenceResult({
        title: `${connectorId} sync`,
        details: [`${payload.status}: ${payload.records_seen} records`, ...payload.actions],
      })
      loadEnterpriseOverview()
    }
  }

  async function evolveCapability() {
    const response = await fetch(`${API_URL}/api/v1/capabilities/evolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        objective: skillGraphObjective,
        observed_gap: evolutionGap,
        category: 'custom',
      }),
    })
    if (response.ok) {
      const payload = await response.json()
      setIntelligenceResult({
        title: payload.proposed_capability.name,
        details: payload.verification_plan,
      })
      loadCapabilities(capabilityQuery)
      loadFeatures()
      loadEnterpriseOverview()
    }
  }

  async function runSkillGraph() {
    const response = await fetch(`${API_URL}/api/v1/skill-graphs/run?dry_run=false`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Workspace graph',
        objective: skillGraphObjective,
        nodes: ['agent.planner', 'capability.evolution_engine', 'reflection.review'],
        edges: [
          { from: 'agent.planner', to: 'capability.evolution_engine' },
          { from: 'capability.evolution_engine', to: 'reflection.review' },
        ],
      }),
    })
    if (response.ok) {
      const payload = await response.json()
      setIntelligenceResult({
        title: payload.name,
        details: payload.execution_plan.map((step: { node: string; status: string }) => `${step.node}: ${step.status}`),
      })
    }
  }

  async function analyzeDomain(kind: 'meeting' | 'vision' | 'trading' | 'robotics') {
    const endpoints = {
      meeting: '/api/v1/meetings/analyze',
      vision: '/api/v1/vision/analyze',
      trading: '/api/v1/trading/analyze',
      robotics: '/api/v1/robotics/readiness',
    }
    const bodies = {
      meeting: { title: 'Workspace analysis', transcript: domainPrompt },
      vision: { description: domainPrompt },
      trading: { symbol: domainPrompt.trim().split(/\s+/)[0] || 'AAPL', strategy: 'balanced', risk_tolerance: 'medium' },
      robotics: { task: domainPrompt, environment: 'lab', safety_constraints: ['human override available'] },
    }
    const response = await fetch(`${API_URL}${endpoints[kind]}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bodies[kind]),
    })
    if (response.ok) {
      const payload = await response.json()
      const details =
        kind === 'meeting'
          ? [payload.summary, ...payload.action_items, ...payload.jira_stories]
          : kind === 'vision'
            ? [...payload.observations, `Risk flags: ${payload.risk_flags.join(', ') || 'none'}`]
            : kind === 'trading'
              ? [`${payload.symbol}: ${payload.signal}`, `Risk ${payload.risk_score}`, ...payload.rationale]
              : [`Readiness ${payload.readiness_score}`, ...payload.blockers, ...payload.checklist]
      setIntelligenceResult({ title: `${kind} result`, details })
    }
  }

  async function sendFeedback(message: Message, rating: 'positive' | 'negative') {
    const response = await fetch(`${API_URL}/api/v1/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rating,
        category: 'response_quality',
        conversation_id: conversationId,
        message_id: message.id,
      }),
    })

    if (response.ok) {
      setFeedbackStatus((current) => ({ ...current, [message.id]: rating }))
      loadFeedbackSummary()
      loadEnterpriseOverview()
    }
  }

  async function saveProfile() {
    const domains = domainInput
      .split(',')
      .map((domain) => domain.trim())
      .filter(Boolean)
    const response = await fetch(`${API_URL}/api/v1/profile`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...profile, domains }),
    })

    if (response.ok) {
      const payload = await response.json()
      setProfile(payload)
      setDomainInput(payload.domains.join(', '))
      loadEnterpriseOverview()
    }
  }

  async function openConversation(id: string) {
    try {
      const response = await fetch(`${API_URL}/api/v1/chat/sessions/${id}`)
      if (!response.ok) {
        throw new Error(`Gateway could not load the chat session (${response.status})`)
      }

      const payload = await response.json()
      setConversationId(typeof payload.id === 'string' ? payload.id : id)
      setMessages(normalizeMessages(payload.messages))
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Unknown gateway error'
      setConversationId(id)
      setMessages([
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `Could not load this conversation. ${detail}`,
          isStreaming: false,
        },
      ])
    }
  }

  async function startNewConversation() {
    setConversationId(null)
    setMessages([])
    setInput('')
  }

  async function ensureConversation(nextTitle = input) {
    if (conversationId) return conversationId

    const response = await fetch(`${API_URL}/api/v1/chat/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: nextTitle.trim().slice(0, 48) || 'Workspace chat' }),
    })
    if (!response.ok) {
      throw new Error(`Gateway could not create a chat session (${response.status})`)
    }
    const conversation = await response.json()
    setConversationId(conversation.id)
    setConversations((current) => [conversation, ...current])
    return conversation.id as string
  }

  function speak(text: string) {
    if (!autoSpeak || !('speechSynthesis' in window)) return

    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 1
    utterance.pitch = 1
    utterance.onstart = () => setVoiceStatus('Speaking response...')
    utterance.onend = () => setVoiceStatus(continuousVoice ? 'Voice session ready.' : 'Speech complete.')
    window.speechSynthesis.speak(utterance)
  }

  async function sendMessageText(rawContent: string) {
    const content = rawContent.trim()
    if (!content || isSending) return

    setInput('')
    setIsSending(true)
    const localMessage: Message = {
      id: `local-${Date.now()}`,
      role: 'user',
      content,
    }
    const streamingMessageId = `stream-${Date.now()}`
    const streamingMessage: Message = {
      id: streamingMessageId,
      role: 'assistant',
      content: '',
      isStreaming: true,
    }
    setMessages((current) => [...current, localMessage, streamingMessage])

    let visibleAssistantContent = ''
    let pendingAssistantContent = ''
    let streamError: Error | null = null
    let flushFrame: number | null = null

    const flushAssistantContent = () => {
      flushFrame = null
      if (!pendingAssistantContent) return

      const nextContent = `${visibleAssistantContent}${pendingAssistantContent}`
      pendingAssistantContent = ''
      visibleAssistantContent = nextContent
      setMessages((current) =>
        updateMessage(current, streamingMessageId, (message) => ({
          ...message,
          content: nextContent,
        })),
      )
    }

    const queueAssistantChunk = (chunk: string) => {
      pendingAssistantContent += chunk
      if (flushFrame !== null) return
      flushFrame = requestAnimationFrame(flushAssistantContent)
    }

    try {
      const id = await ensureConversation(content)
      await apiClient.stream(
        '/api/v1/chat/completions/stream',
        queueAssistantChunk,
        (errorMessage) => {
          streamError = new Error(errorMessage || 'Streaming failed')
        },
        { conversation_id: id, content },
      )

      if (streamError) throw streamError

      if (flushFrame !== null) {
        cancelAnimationFrame(flushFrame)
        flushAssistantContent()
      }

      setMessages((current) =>
        updateMessage(current, streamingMessageId, (message) => ({
          ...message,
          content: visibleAssistantContent || message.content,
          isStreaming: false,
        })),
      )
      if (visibleAssistantContent.trim().length > 0) {
        speak(visibleAssistantContent)
      }
      loadConversations()
      loadMemories(memoryQuery)
    } catch (error) {
      if (flushFrame !== null) {
        cancelAnimationFrame(flushFrame)
      }
      const detail = error instanceof Error ? error.message : 'Unknown gateway error'
      const errorMessage = `Gateway connection failed. ${detail}. Start the gateway with docker compose or uvicorn, then try again.`
      speak(errorMessage)
      setMessages((current) =>
        updateMessage(current, streamingMessageId, () => ({
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: errorMessage,
          isStreaming: false,
        })),
      )
    } finally {
      setIsSending(false)
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await sendMessageText(input)
  }

  function toggleVoiceInput() {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    if (!SpeechRecognition) {
      setVoiceStatus('Voice input is not supported in this browser.')
      return
    }

    if (isListening) {
      recognitionRef.current?.stop()
      setIsListening(false)
      setVoiceStatus('Voice input stopped.')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = 'en-US'
    recognition.continuous = continuousVoice
    recognition.interimResults = true
    recognitionRef.current = recognition
    setIsListening(true)
    setVoiceStatus(continuousVoice ? 'Continuous voice session listening...' : 'Listening...')
    let finalTranscript = ''

    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results)
        .map((result: any) => result[0]?.transcript ?? '')
        .join(' ')
        .trim()
      const finalParts = Array.from(event.results)
        .filter((result: any) => result.isFinal)
        .map((result: any) => result[0]?.transcript ?? '')
        .join(' ')
        .trim()

      if (transcript) {
        setInput(transcript)
      }
      if (finalParts) {
        finalTranscript = finalParts
      }
    }

    recognition.onerror = () => {
      setIsListening(false)
      setVoiceStatus('Voice input could not start. Check microphone permission.')
    }

    recognition.onend = () => {
      setIsListening(false)
      setVoiceStatus((current) =>
        current.includes('Listening') || current.includes('listening') ? 'Voice captured.' : current,
      )
      if (continuousVoice && finalTranscript) {
        void sendMessageText(finalTranscript)
      }
    }

    recognition.start()
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Cognitive OS</p>
          <h1>ShivaAI Jarvis</h1>
        </div>
        <section className="auth-panel" aria-label="User authentication">
          {user ? (
            <>
              <div>
                <strong>{user.full_name || user.email}</strong>
                <small>{user.role}</small>
              </div>
              <button type="button" onClick={logout}>
                Sign out
              </button>
            </>
          ) : (
            <form onSubmit={submitAuth}>
              <div className="auth-tabs" role="tablist" aria-label="Auth mode">
                <button
                  className={authMode === 'login' ? 'active' : ''}
                  type="button"
                  onClick={() => setAuthMode('login')}
                >
                  Login
                </button>
                <button
                  className={authMode === 'signup' ? 'active' : ''}
                  type="button"
                  onClick={() => setAuthMode('signup')}
                >
                  Sign up
                </button>
              </div>
              <input
                value={authEmail}
                onChange={(event) => setAuthEmail(event.target.value)}
                placeholder="Email"
                type="email"
                aria-label="Email"
              />
              <input
                value={authPassword}
                onChange={(event) => setAuthPassword(event.target.value)}
                placeholder="Password"
                type="password"
                aria-label="Password"
              />
              {authMode === 'signup' ? (
                <>
                  <input
                    value={authName}
                    onChange={(event) => setAuthName(event.target.value)}
                    placeholder="Full name"
                    aria-label="Full name"
                  />
                  <select
                    value={authRole}
                    onChange={(event) => setAuthRole(event.target.value)}
                    aria-label="Role"
                  >
                    <option value="user">User</option>
                    <option value="analyst">Analyst</option>
                    <option value="trader">Trader</option>
                    <option value="admin">Admin</option>
                  </select>
                </>
              ) : null}
              <button type="submit">{authMode === 'signup' ? 'Create account' : 'Login'}</button>
            </form>
          )}
          {authMessage ? <small className="auth-message">{authMessage}</small> : null}
          {adminUsers.length > 0 ? (
            <div className="admin-users">
              <strong>Users</strong>
              {adminUsers.map((adminUser) => (
                <span key={adminUser.id}>
                  {adminUser.email} - {adminUser.role}
                </span>
              ))}
            </div>
          ) : null}
        </section>
        <button className="new-chat" type="button" onClick={startNewConversation}>
          New chat
        </button>
        <nav className="conversation-list" aria-label="Saved conversations">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={conversation.id === conversationId ? 'active' : ''}
              type="button"
              onClick={() => openConversation(conversation.id)}
            >
              <span>{conversation.title}</span>
              <small>{conversation.message_count} messages</small>
            </button>
          ))}
        </nav>
        <div className={`status status-${health}`}>
          <span />
          Gateway {health}
        </div>
      </aside>

      <ChatWorkspace
        messages={messages}
        messageListRef={messageListRef}
        feedbackStatus={feedbackStatus}
        input={input}
        isSending={isSending}
        isListening={isListening}
        autoSpeak={autoSpeak}
        continuousVoice={continuousVoice}
        voiceStatus={voiceStatus}
        isModuleEnabled={isModuleEnabled}
        setInput={setInput}
        setAutoSpeak={setAutoSpeak}
        setContinuousVoice={setContinuousVoice}
        setVoiceStatus={setVoiceStatus}
        sendMessage={sendMessage}
        toggleVoiceInput={toggleVoiceInput}
        sendFeedback={sendFeedback}
      />

      <aside className="memory-panel" aria-label="Memory workspace">
        <div className="workspace-tabs" role="tablist" aria-label="Workspace tabs">
          {(['command', 'profile', 'knowledge', 'kernel', 'intelligence', 'settings'] as WorkspaceTab[]).map((tab) => (
            <button
              key={tab}
              className={activeWorkspace === tab ? 'active' : ''}
              type="button"
              onClick={() => setActiveWorkspace(tab)}
            >
              {tab === 'command'
                ? 'Command'
                : tab === 'profile'
                ? 'Profile'
                : tab === 'knowledge'
                  ? 'Knowledge'
                  : tab === 'kernel'
                    ? 'Kernel'
                    : tab === 'intelligence'
                      ? 'Intel'
                      : 'Settings'}
            </button>
          ))}
        </div>

        {activeWorkspace === 'command' ? (
          <div className="command-section">
            <div className="command-hero">
              <div>
                <p className="eyebrow">Enterprise Command</p>
                <h2>Operational readiness</h2>
                <small>
                  {enterpriseOverview
                    ? `Generated ${new Date(enterpriseOverview.generated_at).toLocaleTimeString()}`
                    : 'Waiting for gateway overview'}
                </small>
              </div>
              <div className={`readiness-dial readiness-${enterpriseOverview?.posture ?? 'attention'}`}>
                <strong>{enterpriseOverview?.readiness_score ?? '--'}</strong>
                <span>{enterpriseOverview?.posture ?? 'loading'}</span>
              </div>
            </div>

            <div className="metric-grid" aria-label="Enterprise metrics">
              {enterpriseOverview
                ? [
                    ['Chats', enterpriseOverview.metrics.conversations],
                    ['Memory', enterpriseOverview.metrics.memories],
                    ['Docs', enterpriseOverview.metrics.documents],
                    ['Flows', enterpriseOverview.metrics.workflows],
                    ['Runs', enterpriseOverview.metrics.workflow_runs],
                    ['Caps', enterpriseOverview.metrics.capabilities],
                    ['Conn', enterpriseOverview.metrics.connectors],
                    ['Feedback', enterpriseOverview.metrics.feedback],
                  ].map(([label, value]) => (
                    <article key={label}>
                      <span>{label}</span>
                      <strong>{value}</strong>
                    </article>
                  ))
                : Array.from({ length: 8 }).map((_, index) => (
                    <article key={index}>
                      <span>Loading</span>
                      <strong>--</strong>
                    </article>
                  ))}
            </div>

            <article className="governance-card">
              <div>
                <strong>Governance posture</strong>
                <button type="button" onClick={loadEnterpriseOverview}>
                  Refresh
                </button>
              </div>
              <div className="governance-bars">
                <span>
                  Modules{' '}
                  <b>
                    {enterpriseOverview?.governance.enabled_modules ?? 0}/
                    {enterpriseOverview?.governance.total_modules ?? 0}
                  </b>
                </span>
                <progress
                  value={enterpriseOverview?.governance.enabled_modules ?? 0}
                  max={enterpriseOverview?.governance.total_modules || 1}
                />
                <span>
                  Capabilities{' '}
                  <b>
                    {enterpriseOverview?.governance.enabled_capabilities ?? 0}/
                    {enterpriseOverview?.governance.total_capabilities ?? 0}
                  </b>
                </span>
                <progress
                  value={enterpriseOverview?.governance.enabled_capabilities ?? 0}
                  max={enterpriseOverview?.governance.total_capabilities || 1}
                />
              </div>
              <small>
                LLM {enterpriseOverview?.llm.status ?? 'unknown'} via{' '}
                {enterpriseOverview?.llm.provider ?? 'gateway'}:{' '}
                {enterpriseOverview?.llm.model ?? 'not loaded'}
              </small>
            </article>

            <div className="command-lists">
              <section>
                <strong>Risks</strong>
                {(enterpriseOverview?.risks ?? ['Overview not loaded yet.']).map((risk) => (
                  <p key={risk}>{risk}</p>
                ))}
              </section>
              <section>
                <strong>Next actions</strong>
                {(enterpriseOverview?.next_actions ?? ['Refresh the overview after gateway startup.']).map((action) => (
                  <p key={action}>{action}</p>
                ))}
              </section>
            </div>

            <div className="activity-feed">
              <strong>Recent activity</strong>
              {(enterpriseOverview?.recent_activity ?? []).length > 0 ? (
                enterpriseOverview?.recent_activity.map((activity) => (
                  <article key={`${activity.type}-${activity.created_at}-${activity.label}`}>
                    <span>{activity.label}</span>
                    <small>
                      {activity.type} - {activity.status} -{' '}
                      {new Date(activity.created_at).toLocaleTimeString()}
                    </small>
                  </article>
                ))
              ) : (
                <article>
                  <span>No audited activity yet</span>
                  <small>Run a capability or workflow to populate the feed.</small>
                </article>
              )}
            </div>
          </div>
        ) : null}

        {activeWorkspace === 'profile' ? (
          <>
          <div className="profile-section">

          <div>

            <p className="eyebrow">Profile</p>
            <h2>Jarvis style</h2>
          </div>
          <label>
            Name
            <input
              value={profile.preferred_name ?? ''}
              onChange={(event) =>
                setProfile((current) => ({ ...current, preferred_name: event.target.value }))
              }
              placeholder="Keerthi"
            />
          </label>
          <div className="profile-grid">
            <label>
              Style
              <select
                value={profile.communication_style}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    communication_style: event.target.value,
                  }))
                }
              >
                <option value="concise">Concise</option>
                <option value="balanced">Balanced</option>
                <option value="warm">Warm</option>
                <option value="technical">Technical</option>
              </select>
            </label>
            <label>
              Detail
              <select
                value={profile.response_detail}
                onChange={(event) =>
                  setProfile((current) => ({ ...current, response_detail: event.target.value }))
                }
              >
                <option value="brief">Brief</option>
                <option value="balanced">Balanced</option>
                <option value="detailed">Detailed</option>
              </select>
            </label>
          </div>
          <label>
            Domains
            <input
              value={domainInput}
              onChange={(event) => setDomainInput(event.target.value)}
              placeholder="coding, trading, automation"
            />
          </label>
          <button type="button" onClick={saveProfile}>
            Save profile
          </button>
        </div>

        <div>
          <p className="eyebrow">Memory</p>
          <h2>Semantic recall</h2>
        </div>
        <div className="feedback-summary" aria-label="Feedback summary">
          <strong>Feedback signals</strong>
          <div>
            <span>{feedbackSummary.total} total</span>
            <span>{feedbackSummary.by_rating.positive ?? 0} good</span>
            <span>{feedbackSummary.by_rating.negative ?? 0} fixes</span>
          </div>
        </div>
        <label>
          Add memory
          <textarea
            value={memoryInput}
            onChange={(event) => setMemoryInput(event.target.value)}
            rows={4}
            placeholder="Remember user preferences, project facts, or recurring context"
          />
        </label>
        <button type="button" onClick={saveMemory}>
          Save memory
        </button>
        <form className="memory-search" onSubmit={searchMemory}>
          <input
            value={memoryQuery}
            onChange={(event) => setMemoryQuery(event.target.value)}
            placeholder="Search memory"
            aria-label="Search memory"
          />
        </form>
        <div className="memory-list">
          {memories.map((memory) => (
            <article key={memory.id}>
              <strong>{memory.category}</strong>
              <p>{memory.content}</p>
              <small>
                {memory.source}
                {memory.relevance ? ` - ${Math.round(memory.relevance * 100)}% match` : ''}
              </small>
            </article>
          ))}
        </div>
          </>



        ) : null}

        {activeWorkspace === 'knowledge' ? (
        <div className="knowledge-section">
          <div>
            <p className="eyebrow">Knowledge</p>
            <h2>Documents</h2>
          </div>
          <label>
            Title
            <input
              value={documentTitle}
              onChange={(event) => setDocumentTitle(event.target.value)}
              placeholder="Architecture notes"
            />
          </label>
          <textarea
            value={documentContent}
            onChange={(event) => setDocumentContent(event.target.value)}
            rows={4}
            placeholder="Paste document text to chunk and index"
            aria-label="Document content"
          />
          <input
            value={documentTags}
            onChange={(event) => setDocumentTags(event.target.value)}
            placeholder="rag, roadmap, design"
            aria-label="Document tags"
          />
          <button type="button" onClick={saveDocument}>
            Ingest document
          </button>
          <div className="document-list">
            {documents.map((document) => (
              <article key={document.id}>
                <strong>{document.title}</strong>
                <small>
                  {document.chunk_count} chunks - {document.source}
                </small>
              </article>
            ))}
          </div>
        </div>
        ) : null}

        {activeWorkspace === 'kernel' ? (
        <div className="capability-section">
          <div>
            <p className="eyebrow">Kernel</p>
            <h2>Capabilities</h2>
          </div>

          <div className="feature-grid">
            {features.map((feature) => (
              <article key={feature.id}>
                <strong>{feature.name}</strong>
                <span className={`pill pill-${feature.status}`}>{feature.status}</span>
                <small>{feature.capability_count} linked</small>
              </article>
            ))}
          </div>

          <label>
            Register capability
            <input
              value={capabilityName}
              onChange={(event) => setCapabilityName(event.target.value)}
              placeholder="custom.research.brief"
            />
          </label>
          <textarea
            value={capabilityDescription}
            onChange={(event) => setCapabilityDescription(event.target.value)}
            rows={3}
            placeholder="Describe what this capability can do"
            aria-label="Capability description"
          />
          <button type="button" onClick={saveCapability}>
            Add capability
          </button>

          <form className="memory-search" onSubmit={searchCapabilities}>
            <input
              value={capabilityQuery}
              onChange={(event) => setCapabilityQuery(event.target.value)}
              placeholder="Search capabilities"
              aria-label="Search capabilities"
            />
          </form>
          <div className="capability-list">
            {capabilities.map((capability) => (
              <article key={capability.id}>
                <div>
                  <strong>{capability.name}</strong>
                  <span className={`pill pill-${capability.status}`}>{capability.status}</span>
                </div>
                <p>{capability.description}</p>
                <small>{capability.category}</small>
                <div className="capability-actions">
                  <button
                    type="button"
                    disabled={capability.status !== 'enabled'}
                    onClick={() => invokeCapability(capability.id, true)}
                  >
                    Preview
                  </button>
                  <button
                    type="button"
                    disabled={capability.status !== 'enabled'}
                    onClick={() => invokeCapability(capability.id, false)}
                  >
                    Run
                  </button>
                </div>
              </article>
            ))}
          </div>

          <div className="invocation-list">
            <strong>Recent invocations</strong>
            {invocations.map((invocation) => (
              <article key={invocation.id}>
                <span>{invocation.capability_name}</span>
                <small>
                  {invocation.dry_run ? 'preview' : invocation.status} -{' '}
                  {new Date(invocation.created_at).toLocaleTimeString()}
                </small>
              </article>
            ))}
          </div>

          <div className="ops-section">
            <div>
              <p className="eyebrow">Workflow</p>
              <h2>Local operations</h2>
            </div>
            <input
              value={workflowName}
              onChange={(event) => setWorkflowName(event.target.value)}
              placeholder="Release readiness"
              aria-label="Workflow name"
            />
            <textarea
              value={workflowSteps}
              onChange={(event) => setWorkflowSteps(event.target.value)}
              rows={3}
              placeholder="One workflow step per line"
              aria-label="Workflow steps"
            />
            <button type="button" onClick={saveWorkflow}>
              Save workflow
            </button>
            <div className="workflow-list">
              {workflows.map((workflow) => (
                <article key={workflow.id}>
                  <strong>{workflow.name}</strong>
                  <small>{workflow.steps.length} steps - {workflow.status}</small>
                  <div>
                    <button type="button" onClick={() => runWorkflow(workflow.id, true)}>
                      Preview
                    </button>
                    <button type="button" onClick={() => runWorkflow(workflow.id, false)}>
                      Run
                    </button>
                  </div>
                </article>
              ))}
            </div>
            <div className="invocation-list">
              <strong>Workflow runs</strong>
              {latestWorkflowRun && (
                <article>
                  <span>{latestWorkflowRun.workflow_name}</span>
                  <small>
                    {latestWorkflowRun.dry_run ? 'preview' : latestWorkflowRun.status} -{' '}
                    {latestWorkflowRun.output?.execution_mode ?? 'workflow'}
                  </small>
                  {workflowFinalResponse(latestWorkflowRun.output) && (
                    <p>{workflowFinalResponse(latestWorkflowRun.output)}</p>
                  )}
                  <small>
                    Domains: {workflowDomains(latestWorkflowRun.output).join(', ') || 'none'} - Knowledge:{' '}
                    {workflowKnowledgeCount(latestWorkflowRun.output)}
                  </small>
                </article>
              )}
              {workflowRuns.map((run) => (
                <article key={run.id}>
                  <span>{run.workflow_name}</span>
                  <small>
                    {run.dry_run ? 'preview' : run.status} -{' '}
                    {new Date(run.created_at).toLocaleTimeString()}
                  </small>
                </article>
              ))}
            </div>
          </div>

          <div className="ops-section">
            <div>
              <p className="eyebrow">Decision</p>
              <h2>Score & reflect</h2>
            </div>
            <textarea
              value={decisionText}
              onChange={(event) => setDecisionText(event.target.value)}
              rows={3}
              placeholder="Decision to evaluate"
              aria-label="Decision to evaluate"
            />
            <button type="button" onClick={evaluateDecision}>
              Evaluate decision
            </button>
            {decisionResult ? (
              <article className="decision-result">
                <strong>{decisionResult.recommendation}</strong>
                <div>
                  <span>Confidence {decisionResult.confidence_score}</span>
                  <span>Risk {decisionResult.risk_score}</span>
                  <span>Cost {decisionResult.cost_score}</span>
                  <span>Impact {decisionResult.impact_score}</span>
                </div>
              </article>
            ) : null}
            <textarea
              value={reflectionText}
              onChange={(event) => setReflectionText(event.target.value)}
              rows={3}
              placeholder="Content to review"
              aria-label="Content to review"
            />
            <button type="button" onClick={reviewReflection}>
              Review content
            </button>
            {reflectionResult ? (
              <article className="decision-result">
                <strong>Quality {reflectionResult.quality_score}</strong>
                <p>{reflectionResult.summary}</p>
                <small>{reflectionResult.improvements.join(' ')}</small>
              </article>
            ) : null}
          </div>
        </div>
        ) : null}

        {activeWorkspace === 'intelligence' ? (
        <div className="capability-section">
          <div>
            <p className="eyebrow">Architecture</p>
            <h2>Intelligence modules</h2>
          </div>

          <div className="ops-section">
            <strong>Digital twin</strong>
            {digitalTwin ? (
              <article className="decision-result">
                <strong>{digitalTwin.preferred_name || 'Local profile'}</strong>
                <p>{digitalTwin.inferred_work_style}</p>
                <small>
                  {digitalTwin.known_facts.length} facts - {digitalTwin.domains.join(', ') || 'no domains'}
                </small>
              </article>
            ) : null}
            <textarea
              value={worldFact}
              onChange={(event) => setWorldFact(event.target.value)}
              rows={3}
              placeholder="Subject relation object"
              aria-label="World fact"
            />
            <button type="button" onClick={saveWorldFact}>
              Save fact
            </button>
          </div>

          <div className="ops-section">
            <strong>Enterprise connectors</strong>
            <input
              value={connectorQuery}
              onChange={(event) => setConnectorQuery(event.target.value)}
              placeholder="Connector search query"
              aria-label="Connector search query"
            />
            <div className="connector-grid">
              {connectors.map((connector) => (
                <article key={connector.id}>
                  <strong>{connector.provider}</strong>
                  <small>{connector.status}</small>
                  <div>
                    <button type="button" onClick={() => runConnectorSearch(connector.id)}>
                      Search
                    </button>
                    <button type="button" onClick={() => syncConnector(connector.id)}>
                      Sync
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="ops-section">
            <strong>Skill graph & evolution</strong>
            <textarea
              value={skillGraphObjective}
              onChange={(event) => setSkillGraphObjective(event.target.value)}
              rows={2}
              placeholder="Skill graph objective"
              aria-label="Skill graph objective"
            />
            <textarea
              value={evolutionGap}
              onChange={(event) => setEvolutionGap(event.target.value)}
              rows={2}
              placeholder="Observed capability gap"
              aria-label="Observed capability gap"
            />
            <div className="capability-actions">
              <button type="button" onClick={runSkillGraph}>
                Run graph
              </button>
              <button type="button" onClick={evolveCapability}>
                Evolve
              </button>
            </div>
          </div>

          <div className="ops-section">
            <strong>Domain intelligence</strong>
            <textarea
              value={domainPrompt}
              onChange={(event) => setDomainPrompt(event.target.value)}
              rows={3}
              placeholder="Describe meeting, screen, symbol, or robotics task"
              aria-label="Domain prompt"
            />
            <div className="domain-actions">
              <button type="button" onClick={() => analyzeDomain('meeting')}>
                Meeting
              </button>
              <button type="button" onClick={() => analyzeDomain('vision')}>
                Vision
              </button>
              <button type="button" onClick={() => analyzeDomain('trading')}>
                Trading
              </button>
              <button type="button" onClick={() => analyzeDomain('robotics')}>
                Robotics
              </button>
            </div>
          </div>

          {intelligenceResult ? (
            <article className="decision-result">
              <strong>{intelligenceResult.title}</strong>
              {intelligenceResult.details.map((detail) => (
                <p key={detail}>{detail}</p>
              ))}
            </article>
          ) : null}
        </div>
        ) : null}

        {activeWorkspace === 'settings' ? (
        <div className="capability-section">
          <div>
            <p className="eyebrow">Settings</p>
            <h2>Feature modules</h2>
          </div>
          {settingsMessage ? <p className="settings-message">{settingsMessage}</p> : null}
          <div className="settings-list">
            {moduleSettings.map((setting) => (
              <article key={setting.id}>
                <div>
                  <strong>{setting.name}</strong>
                  <span>{setting.category}</span>
                </div>
                <p>{setting.description}</p>
                <label>
                  <input
                    type="checkbox"
                    checked={setting.enabled}
                    onChange={(event) => updateModuleSetting(setting.id, event.target.checked)}
                  />
                  {setting.enabled ? 'Enabled' : 'Disabled'}
                </label>
              </article>
            ))}
          </div>
        </div>
        ) : null}
      </aside>
    </main>
  )
}
