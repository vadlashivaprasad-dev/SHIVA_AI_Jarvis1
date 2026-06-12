import type { Message } from './types'

export function updateMessage(
  messages: Message[],
  messageId: string,
  update: (message: Message) => Message,
) {
  return messages.map((message) => (message.id === messageId ? update(message) : message))
}

export function normalizeMessages(value: unknown): Message[] {
  if (!Array.isArray(value)) return []

  return value
    .filter((message): message is Partial<Message> & { content: string; role: Message['role'] } => {
      if (!message || typeof message !== 'object') return false
      const maybeMessage = message as Partial<Message>
      return (
        (maybeMessage.role === 'user' || maybeMessage.role === 'assistant') &&
        typeof maybeMessage.content === 'string'
      )
    })
    .map((message, index) => ({
      id: typeof message.id === 'string' ? message.id : `message-${Date.now()}-${index}`,
      role: message.role,
      content: message.content,
      isStreaming: Boolean(message.isStreaming),
    }))
}
