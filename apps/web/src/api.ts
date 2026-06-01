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
    options: RequestInit & { method?: string } = {}
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

  // Streaming responses for chat
  async stream(
    endpoint: string,
    onChunk: (chunk: string) => void,
    onError: (error: string) => void
  ): Promise<void> {
    const url = `${API_URL}${endpoint}`

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: this.getHeaders(),
      })

      if (!response.ok) {
        const error = await response.json()
        onError(error.user_message || error.message)
        return
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data) onChunk(data)
          }
        }
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Connection error')
    }
  }
}

export const apiClient = new ApiClient()
