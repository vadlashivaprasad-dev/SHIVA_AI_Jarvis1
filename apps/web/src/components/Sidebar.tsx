// Sidebar Component - Navigation and user info
import React, { useEffect, useState } from 'react'
import { useAppStore, User } from '../store'
import { apiClient } from '../api'
import { Button, Skeleton } from './ui'

interface SidebarProps {
  onLogout: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({ onLogout }) => {
  const { user, setUser, isLoading } = useAppStore()
  const [health, setHealth] = useState<'healthy' | 'error'>('error')

  useEffect(() => {
    checkHealth()
  }, [])

  const checkHealth = async () => {
    try {
      const response = await fetch('/health')
      const data = await response.json()
      setHealth(data.status === 'healthy' ? 'healthy' : 'error')
    } catch {
      setHealth('error')
    }
  }

  return (
    <aside className="w-64 bg-gradient-to-b from-gray-900 to-gray-800 text-white border-r border-gray-700 flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-gray-700">
        <h1 className="text-2xl font-bold">ShivaAI</h1>
        <p className="text-sm text-gray-400 mt-1">Jarvis Assistant</p>
      </div>

      {/* Health Status */}
      <div className="px-6 py-4 flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${
            health === 'healthy' ? 'bg-green-500' : 'bg-red-500'
          }`}
        />
        <span className="text-xs text-gray-400">
          {health === 'healthy' ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      {/* User Info */}
      <div className="px-6 py-4 border-t border-gray-700">
        {isLoading ? (
          <Skeleton className="h-12 w-full" />
        ) : user ? (
          <div className="space-y-2">
            <p className="font-medium text-sm">{user.full_name || user.email}</p>
            <p className="text-xs text-gray-400">{user.role}</p>
            <Button
              variant="secondary"
              size="sm"
              onClick={onLogout}
              className="w-full mt-2"
            >
              Logout
            </Button>
          </div>
        ) : (
          <p className="text-gray-400 text-sm">Not logged in</p>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-6 py-4 space-y-2">
        <NavLink icon="💬" label="Chat" />
        <NavLink icon="💾" label="Memory" />
        <NavLink icon="📄" label="Documents" />
        <NavLink icon="⚙️" label="Settings" />
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-gray-700 text-xs text-gray-400">
        <p>v1.0.0</p>
      </div>
    </aside>
  )
}

const NavLink: React.FC<{ icon: string; label: string }> = ({
  icon,
  label,
}) => (
  <button className="w-full text-left px-4 py-2 rounded-lg text-gray-300 hover:bg-gray-700 hover:text-white transition-colors flex items-center gap-3">
    <span>{icon}</span>
    <span className="text-sm">{label}</span>
  </button>
)
