// API client with proper error handling and request/response management
import { useAppStore } from './store'

const DEFAULT_API_URL = import.meta.env.VITE_API_URL || ''
const API_URL = DEFAULT_API_URL.replace(/\/$/, '')

function extractStreamText(value: unknown): string {
  const textFromObject = (payload: unknown): string | null => {
    if (typeof payload === 'string') return payload
    if (!payload || typeof payload !== 'object') return null

    const record = payload as { text?: unknown; content?: unknown; message?: unknown }
    if (typeof record.text === 'string') return record.text
    if (typeof record.content === 'string') return record.content
    if (typeof record.message === 'string') return record.message
    return null
  }

  if (typeof value !== 'string') {
    const objectText = textFromObject(value)
    return objectText === null ? '' : extractStreamText(objectText)
  }

  try {
    const parsed = JSON.parse(value)
    const parsedText = textFromObject(parsed)
    if (parsedText !== null) return extractStreamText(parsedText)
  } catch {
    // Fall through to embedded JSON-object cleanup.
  }

  let output = ''
  let cursor = 0
  let foundEmbeddedPayload = false

  while (cursor < value.length) {
    const start = value.indexOf('{', cursor)
    if (start === -1) {
      output += value.slice(cursor)
      break
    }

    output += value.slice(cursor, start)

    let depth = 0
    let inString = false
    let escape = false
    let end = -1

    for (let index = start; index < value.length; index += 1) {
      const char = value[index]

      if (inString) {
        if (escape) {
          escape = false
        } else if (char === '\\') {
          escape = true
        } else if (char === '"') {
          inString = false
        }
        continue
      }

      if (char === '"') {
        inString = true
      } else if (char === '{') {
        depth += 1
      } else if (char === '}') {
        depth -= 1
        if (depth === 0) {
          end = index
          break
        }
      }
    }

    if (end === -1) {
      output += value.slice(start)
      break
    }

    const objectText = value.slice(start, end + 1)
    try {
      const text = textFromObject(JSON.parse(objectText))
      if (text !== null) {
        output += text
        foundEmbeddedPayload = true
      } else {
        output += objectText
      }
    } catch {
      output += objectText
    }

    cursor = end + 1
  }

  return foundEmbeddedPayload ? output : value
}

export interface ApiError {
  code: string
  message: string
  user_message: string
  request_id: string
  severity: 'info' | 'warning' | 'error' | 'critical'
  status_code: number
}

export class ApiClient {
  private getHeaders(): HeadersInit {
    const storeToken = useAppStore.getState().token
    const legacyToken =
      typeof window !== 'undefined' ? localStorage.getItem('shivaai_access_token') : null
    const token = storeToken || legacyToken
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }
  }

  async request<T>(
    endpoint: string,
    options: RequestInit & { method?: string } = {},
  ): Promise<T> {
    const url = `${API_URL}${endpoint}`
    const method = options.method || 'GET'

    try {
      const response = await fetch(url, {
        ...options,
        method,
        headers: this.getHeaders(),
      })

      const data: unknown = await response.json()

      if (!response.ok) {
        const error = data as ApiError
        useAppStore.setState({
          error: error.user_message || error.message,
        })
        throw error
      }

      return data as T
    } catch (error) {
      if (error instanceof Error) {
        useAppStore.setState({ error: error.message })
      }
      throw error
    }
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async post<T>(endpoint: string, body?: Record<string, any>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  async patch<T>(endpoint: string, body?: Record<string, any>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }

  // Streaming responses for chat (SSE/legacy JSON)
  async stream(
    endpoint: string,
    onChunk: (chunk: string) => void,
    onError: (error: string) => void,
    body?: Record<string, any>,
    signal?: AbortSignal,
  ): Promise<void> {
    const url = `${API_URL}${endpoint}`

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: this.getHeaders(),
        body: body ? JSON.stringify(body) : undefined,
        signal,
      })

      if (!response.ok) {
        const error = (await response.json()) as Partial<ApiError> | any
        const payload = typeof error === 'object' && error ? error : { message: String(error) }
        onError(JSON.stringify(payload))
        return
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()

      const contentType = response.headers.get('content-type') ?? ''
      const isSseStream = contentType.toLowerCase().includes('text/event-stream')

      // SSE parsing buffer
      let sseBuffer = ''

      // Legacy raw JSON parsing buffer: expects concatenated JSON objects that represent tokens.
      // Example: {"text":"I can "}{"text":"help "}{"text":"you"}
      let jsonBuffer = ''

      // Extract complete SSE frames from sseBuffer.
      // We only process parts ending with double newline delimiter.
      const tryExtractSseFrames = (emitFrame: (frame: string) => void) => {
        const parts = sseBuffer.split('\n\n')
        sseBuffer = parts.pop() || ''
        for (const frame of parts) {
          if (frame.trim().length === 0) continue
          emitFrame(frame)
        }
      }

      const parseSseFrame = (frame: string): { event?: string; data?: string } => {
        const lines = frame.split('\n').map((l) => l.trimEnd().replace(/\r$/, ''))
        const eventLine = lines.find((l) => l.startsWith('event: '))
        const event = eventLine ? eventLine.slice(7).trim() : undefined

        const dataLines = lines.filter((l) => l.startsWith('data: '))
        const data = dataLines
          .map((l) => l.slice(6))
          .join('\n')
          .replace(/\\n/g, '\n')

        return { event, data }
      }

      // Extract complete JSON objects from jsonBuffer.
      // Uses a lightweight brace matcher that respects strings/escapes.
      const tryExtractJsonObjects = (): void => {
        while (true) {
          const start = jsonBuffer.indexOf('{')
          if (start === -1) {
            jsonBuffer = ''
            return
          }

          let depth = 0
          let inString = false
          let escape = false
          let end = -1

          for (let i = start; i < jsonBuffer.length; i++) {
            const ch = jsonBuffer[i]

            if (inString) {
              if (escape) {
                escape = false
              } else if (ch === '\\') {
                escape = true
              } else if (ch === '"') {
                inString = false
              }
              continue
            }

            if (ch === '"') {
              inString = true
              continue
            }

            if (ch === '{') depth++
            else if (ch === '}') {
              depth--
              if (depth === 0) {
                end = i
                break
              }
            }
          }

          if (end === -1) return // incomplete trailing fragment

          const objStr = jsonBuffer.slice(start, end + 1)
          jsonBuffer = jsonBuffer.slice(end + 1)

          try {
            const parsed = JSON.parse(objStr)
            const text = extractStreamText(parsed)

            if (text) onChunk(text)
          } catch {
            // Malformed JSON: stop extracting to avoid passing raw payload.
            // Keep remaining buffer as-is and wait for more data.
            // (If it never becomes valid, the stream will finish; UI will show fallback error.)
            return
          }
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const incoming = decoder.decode(value, { stream: true })

        if (isSseStream || incoming.includes('event:') || incoming.includes('data:')) {
          sseBuffer += incoming

          tryExtractSseFrames((frame) => {
            const { event, data } = parseSseFrame(frame)
            if (!data) return

            // Stop marker
            if (data.trim() === '[DONE]') return

            if (event === 'error') {
              onError(data)
              return
            }

            if (event === 'done') {
              return
            }

            if (event === 'token') {
              const text = extractStreamText(data)
              if (text) onChunk(text)
              return
            }

            // Some backends may not send `event:` line, only data payload.
            // Treat any JSON in `data` as token payload.
            try {
              const parsed = JSON.parse(data)
              const text = extractStreamText(parsed)
              if (text) onChunk(text)
            } catch {
              // Ignore non-JSON SSE data to avoid showing raw wrappers.
            }
          })
        } else {
          jsonBuffer += incoming
          tryExtractJsonObjects()
        }

        // If SSE stream used [DONE] sentinel without an event line, stop will be handled by server closing.
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      onError(error instanceof Error ? error.message : 'Connection error')
    }
  }
}

export const apiClient = new ApiClient()

