// API client with proper error handling and request/response management
import { useAppStore } from './store'

const DEFAULT_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_URL = DEFAULT_API_URL.replace(/\/$/, '')

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
    const token = useAppStore.getState().token
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

  // Streaming responses for chat (SSE)
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
        // Preserve structured gateway error fields (e.g., code=RES_001)
        const error = (await response.json()) as Partial<ApiError> | any
        const payload = typeof error === 'object' && error ? error : { message: String(error) }
        onError(JSON.stringify(payload))
        return
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      const handleBlock = (block: string) => {
        const lines = block.split('\n').map((l) => l.trimEnd())
        const eventLine = lines.find((l) => l.startsWith('event: '))
        const event = eventLine ? eventLine.slice(7).trim() : undefined

        const dataLines = lines.filter((l) => l.startsWith('data: '))
        const data = dataLines
          .map((l) => l.slice(6))
          .join('\n')
          .replace(/\\n/g, '\n')

        return { event, data }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() || ''

        for (const block of blocks) {
          const { event, data } = handleBlock(block)
          if (!data) continue

          if (event === 'token') {
            onChunk(data)
            continue
          }

          if (event === 'done') return

          if (event === 'error') {
            onError(data)
            return
          }
        }
      }
    } catch (error) {
      // Abort should be silent; caller decides UX.
      if (error instanceof DOMException && error.name === 'AbortError') return
      onError(error instanceof Error ? error.message : 'Connection error')
    }
  }
}

export const apiClient = new ApiClient()

