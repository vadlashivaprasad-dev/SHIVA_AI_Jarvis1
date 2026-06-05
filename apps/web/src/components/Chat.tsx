// ChatComponent - enterprise-ready AI chat UI (backward compatible)
import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAppStore, type Message, type Conversation } from '../store'
import { apiClient } from '../api'
import { Button, Input, Skeleton, Alert } from './ui'
import { Bot, Copy, MessageSquare, Plus, RefreshCw, Send, User, AlertCircle } from 'lucide-react'

type ChatMessageStatus = 'sending' | 'sent' | 'failed'

type ChatMessageView = Message & {
  status?: ChatMessageStatus
  timestamp?: string
}

const ConversationItem = memo(function ConversationItem(props: {
  conversation: Conversation
  active: boolean
  onSelect: (id: string) => void
}) {
  const { conversation, active, onSelect } = props

  return (
    <button
      type="button"
      className={
        'w-full text-left p-2 rounded text-sm truncate transition-colors ' +
        (active
          ? 'bg-blue-100 text-blue-900'
          : 'hover:bg-gray-100 text-gray-700')
      }
      onClick={() => onSelect(conversation.id)}
      aria-current={active ? 'page' : undefined}
    >
      <div className="flex items-center gap-2">
        <MessageSquare size={14} aria-hidden="true" />
        <span className="truncate">{conversation.title}</span>
      </div>
    </button>
  )
})

const MessageBubble = memo(function MessageBubble(props: {
  message: ChatMessageView
  onCopy: (content: string) => void
}) {
  const { message, onCopy } = props
  const isUser = message.role === 'user'

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      role="listitem"
      aria-label={isUser ? 'User message' : 'Assistant message'}
    >
      <div className="max-w-[75%]">
        <div
          className={
            'px-4 py-2 rounded-lg whitespace-pre-wrap break-words ' +
            (isUser
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-900')
          }
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              {isUser ? <User size={16} aria-hidden="true" /> : <Bot size={16} aria-hidden="true" />}
              <p className="text-sm">{message.content}</p>
            </div>

            <button
              type="button"
              className="ml-3 inline-flex items-center gap-1 text-xs opacity-80 hover:opacity-100"
              onClick={() => onCopy(message.content)}
              aria-label="Copy message"
              title="Copy"
            >
              <Copy size={14} aria-hidden="true" />
            </button>
          </div>

          {message.status === 'sending' && !isUser ? (
            <div className="mt-2 text-xs opacity-70 inline-flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-blue-600 animate-pulse" aria-hidden="true" />
              Thinking...
            </div>
          ) : null}

          {!isUser && message.status === 'failed' ? (
            <div className="mt-2 text-xs text-red-700 inline-flex items-center gap-2">
              <AlertCircle size={14} aria-hidden="true" />
              Failed to generate response.
            </div>
          ) : null}
        </div>

        <div className="mt-1 text-[11px] opacity-60">
          {message.timestamp ? new Date(message.timestamp).toLocaleTimeString() : null}
        </div>
      </div>
    </div>
  )
})

export const ChatComponent: React.FC = () => {
  const {
    conversationId,
    messages,
    isLoading,
    error,
    setError,
    setIsLoading,
    addMessage,
    updateMessage,
  } = useAppStore()

  const [input, setInput] = useState('')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [assistantStatusByMessageId, setAssistantStatusByMessageId] = useState<Record<string, ChatMessageStatus>>({})
  const [mounted, setMounted] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    setMounted(true)
    return () => {
      setMounted(false)
    }
  }, [])

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [scrollToBottom, messages, isLoading])

  const loadConversations = useCallback(async () => {
    try {
      const data = await apiClient.get<Conversation[]>('/api/v1/chat/sessions')
      if (!mounted) return
      setConversations(data)
    } catch (err) {
      console.error('Failed to load conversations:', err)
      if (!mounted) return
      setConversations([])
    }
  }, [mounted])

  useEffect(() => {
    void loadConversations()
  }, [loadConversations])

  const handleConversationSelect = useCallback((id: string) => {
    // Keep using store architecture
    useAppStore.setState({ conversationId: id })
  }, [])

  const createNewConversation = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const conversation = await apiClient.post<Conversation>('/api/v1/chat/sessions', {
        title: `Conversation ${new Date().toLocaleTimeString()}`,
      })

      // Avoid stale closure
      setConversations((prev) => [conversation, ...prev])
      return conversation.id
    } catch (err) {
      setError('Failed to create conversation')
      return null
    } finally {
      setIsLoading(false)
    }
  }, [setError, setIsLoading])

  const visibleConversations = useMemo(() => conversations.slice(0, 5), [conversations])

  const copyMessage = useCallback(async (content: string) => {
    try {
      await navigator.clipboard.writeText(content)
    } catch {
      // Fallback: do nothing, keep UX safe
      console.warn('Clipboard write failed')
    }
  }, [])

  const sendMessage = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      const content = input.trim()
      if (!content) return
      if (isLoading) return

      const currentConvId = conversationId ?? (await createNewConversation())
      if (!currentConvId) return

      const userMessageId = crypto.randomUUID()
      const assistantMessageId = crypto.randomUUID()

      const userMessage: Message = {
        id: userMessageId,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      }

      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      }

      // Optimistic updates
      addMessage(userMessage)
      addMessage(assistantMessage)

      setInput('')
      setError(null)
        setAssistantStatusByMessageId((prev) => ({ ...prev, [assistantMessageId]: 'sending' }))
      	setIsLoading(true)

      try {
        // Stream response via SSE so the UI can update incrementally.
        setAssistantStatusByMessageId((prev) => ({ ...prev, [assistantMessageId]: 'sending' }))


        let accumulated = ''
        let finalTimestamp = new Date().toISOString()

        const runStream = async (conversationIdToUse: string) => {
          // NOTE: backend expects conversation_id for resolving conversation.
          // If the conversation is missing (404), we create one and retry.
          await apiClient.stream(
            '/api/v1/chat/completions/stream',
            (chunk: string) => {
              accumulated += chunk
              updateMessage(assistantMessageId, {
                content: accumulated,
                isStreaming: true,
              })
            },
            (errorMessage) => {
              throw new Error(errorMessage)
            },
            {
              conversation_id: conversationIdToUse,
              content,
              model: undefined,
              temperature: 0.7,
              max_tokens: 512,
            },
          )
        }

        const currentConvIdForStream = conversationId ?? currentConvId
        try {
          await runStream(currentConvIdForStream)
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err)
          if (msg.toLowerCase().includes('not found') || msg.includes('RES_001')) {
            const createdId = await createNewConversation()
            if (!createdId) throw err
            await runStream(createdId)
          } else {
            throw err
          }
        }


        updateMessage(assistantMessageId, {
          content: accumulated,
          timestamp: finalTimestamp,
          isStreaming: false,
          role: 'assistant',
        })

        setAssistantStatusByMessageId((prev) => ({ ...prev, [assistantMessageId]: 'sent' }))
      } catch (err) {
        setError('Failed to send message')
        setAssistantStatusByMessageId((prev) => ({ ...prev, [assistantMessageId]: 'failed' }))
        updateMessage(assistantMessageId, {
          isStreaming: false,
          content: '',
          timestamp: new Date().toISOString(),
        })
      } finally {
        setIsLoading(false)
      }
    },
    [
      input,
      isLoading,
      conversationId,
      createNewConversation,
      addMessage,
      updateMessage,
      setError,
      setIsLoading,
    ],
  )


  const regenerateLast = useCallback(async () => {
    // Business logic preservation: simply resends current input if any
    // If there is no input, keep no-op.
    const content = input.trim()
    if (!content) return
    // Trigger send
    setError(null)
    await sendMessage({ preventDefault: () => {} } as unknown as React.FormEvent)
  }, [input, sendMessage, setError])

  const statusByMessage = assistantStatusByMessageId

  return (
    <div className="flex flex-col h-full" aria-label="Chat module">
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center justify-between gap-3">
          <Button variant="primary" size="sm" onClick={() => void createNewConversation()} disabled={isLoading}>
            <Plus size={16} aria-hidden="true" />
            New Chat
          </Button>

          <button
            type="button"
            className="inline-flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900"
            onClick={() => void loadConversations()}
            aria-label="Refresh conversations"
            title="Refresh"
          >
            <RefreshCw size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="mt-4 space-y-2" role="list" aria-label="Conversation list">
          {visibleConversations.length === 0 ? (
            <div className="text-sm text-gray-500">No conversations yet.</div>
          ) : (
            visibleConversations.map((conv) => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                active={conversationId === conv.id}
                onSelect={handleConversationSelect}
              />
            ))
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3" aria-live="polite" aria-relevant="additions">
        {!conversationId ? (
          <div className="flex items-center justify-center h-full text-gray-500 text-sm">Start a new conversation</div>
        ) : null}

        <div role="list" aria-label="Message list">
          {(messages as Message[]).map((msg) => {
            const view: ChatMessageView = {
              ...msg,
              status: statusByMessage[msg.id],
            }

            return <MessageBubble key={msg.id} message={view} onCopy={copyMessage} />
          })}
        </div>

        {isLoading ? (
          <div className="flex justify-start">
            <div className="inline-flex items-center gap-2 text-sm text-gray-600">
              <Bot size={16} aria-hidden="true" />
              <span>Generating response...</span>
            </div>
          </div>
        ) : null}

        <div ref={messagesEndRef} />
      </div>

      {error ? (
        <div className="p-4">
          <Alert type="error" message={error} onClose={() => setError(null)} />
        </div>
      ) : null}

      <form
        onSubmit={sendMessage}
        className="border-t border-gray-200 p-4"
        aria-label="Chat input"
      >
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            disabled={isLoading}
            className="flex-1"
            aria-label="Message text"
          />

          <Button type="submit" disabled={isLoading || !input.trim()} loading={isLoading}>
            <Send size={16} aria-hidden="true" />
            Send
          </Button>
        </div>

        <div className="mt-2 flex items-center justify-between">
          <div className="text-xs text-gray-500">Enter sends • Shift+Enter keeps newline</div>
          {/* No endpoint changes; regeneration kept as optional UX helper */}
          <button
            type="button"
            className="text-xs text-gray-600 hover:text-gray-900 inline-flex items-center gap-1"
            onClick={() => void regenerateLast()}
            aria-label="Retry last message"
            title="Retry"
          >
            <RefreshCw size={14} aria-hidden="true" /> Retry
          </button>
        </div>
      </form>

      {/* Keep existing components; skeleton already used in old implementation */}
      {false ? <Skeleton className="w-32 h-8" /> : null}
    </div>
  )
}

