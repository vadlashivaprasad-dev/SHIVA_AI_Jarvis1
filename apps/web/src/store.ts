// Global state management using Zustand
import { create } from 'zustand'

export interface User {
  id: string
  email: string
  full_name?: string
  role: string
  created_at: string
}

export interface AppState {
  // Auth
  token: string | null
  user: User | null
  setToken: (token: string | null) => void
  setUser: (user: User | null) => void
  
  // Chat
  conversationId: string | null
  messages: Message[]
  setConversationId: (id: string | null) => void
  addMessage: (message: Message) => void
  updateMessage: (id: string, update: Partial<Message>) => void
  clearMessages: () => void
  
  // UI State
  isLoading: boolean
  error: string | null
  setIsLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  
  // Sidebar
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  
  // Health
  apiHealth: 'healthy' | 'error' | 'loading'
  setApiHealth: (status: 'healthy' | 'error' | 'loading') => void
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  isStreaming?: boolean
}

export interface Conversation {
  id: string
  title: string
  updated_at: string
  message_count: number
}

export interface MemoryEntry {
  id: string
  content: string
  category: string
  source: string
  relevance?: number
}

export interface DocumentEntry {
  id: string
  title: string
  source: string
  tags: string[]
  chunk_count: number
}

// Zustand store
export const useAppStore = create<AppState>((set) => ({
  token: localStorage.getItem('shivaai_token') || null,
  user: null,
  conversationId: null,
  messages: [],
  isLoading: false,
  error: null,
  sidebarOpen: true,
  apiHealth: 'loading',

  setToken: (token) => {
    set({ token })
    if (token) {
      localStorage.setItem('shivaai_token', token)
    } else {
      localStorage.removeItem('shivaai_token')
    }
  },

  setUser: (user) => set({ user }),
  setConversationId: (id) => set({ conversationId: id }),
  
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  updateMessage: (id, update) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, ...update } : msg
      ),
    })),

  clearMessages: () => set({ messages: [] }),
  setIsLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setApiHealth: (status) => set({ apiHealth: status }),
}))
