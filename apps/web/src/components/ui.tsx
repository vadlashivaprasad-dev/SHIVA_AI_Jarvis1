// Reusable UI Components

import React from 'react'

// Button Component
export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, children, ...props }, ref) => {
    const variantStyles = {
      primary: 'bg-blue-600 text-white hover:bg-blue-700',
      secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
      danger: 'bg-red-600 text-white hover:bg-red-700',
    }

    const sizeStyles = {
      sm: 'px-3 py-1 text-sm',
      md: 'px-4 py-2 text-base',
      lg: 'px-6 py-3 text-lg',
    }

    return (
      <button
        ref={ref}
        disabled={loading || props.disabled}
        className={`
          inline-flex items-center justify-center gap-2
          rounded-lg font-medium transition-colors
          disabled:opacity-50 disabled:cursor-not-allowed
          ${variantStyles[variant]}
          ${sizeStyles[size]}
        `}
        {...props}
      >
        {loading && <span className="inline-block w-4 h-4 border-2 border-current border-r-transparent rounded-full animate-spin" />}
        {children}
      </button>
    )
  }
)

// Input Component
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, ...props }, ref) => (
    <div className="flex flex-col gap-1">
      {label && <label className="text-sm font-medium text-gray-700">{label}</label>}
      <input
        ref={ref}
        className={`
          px-3 py-2 rounded-lg border
          focus:outline-none focus:ring-2 focus:ring-blue-500
          ${error ? 'border-red-500' : 'border-gray-300'}
        `}
        {...props}
      />
      {error && <span className="text-sm text-red-600">{error}</span>}
    </div>
  )
)

// Card Component
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export const Card: React.FC<CardProps> = ({ className, children, ...props }) => (
  <div
    className={`rounded-lg border border-gray-200 bg-white p-4 shadow-sm ${className}`}
    {...props}
  >
    {children}
  </div>
)

// Loading Skeleton
export const Skeleton: React.FC<{ className?: string }> = ({ className }) => (
  <div className={`bg-gray-200 animate-pulse rounded ${className}`} />
)

// Error Alert
export interface AlertProps {
  title?: string
  message: string
  type?: 'error' | 'warning' | 'success' | 'info'
  onClose?: () => void
}

export const Alert: React.FC<AlertProps> = ({
  title,
  message,
  type = 'info',
  onClose,
}) => {
  const typeStyles = {
    error: 'bg-red-50 text-red-800 border-red-200',
    warning: 'bg-yellow-50 text-yellow-800 border-yellow-200',
    success: 'bg-green-50 text-green-800 border-green-200',
    info: 'bg-blue-50 text-blue-800 border-blue-200',
  }

  return (
    <div className={`rounded-lg border p-4 ${typeStyles[type]}`}>
      <div className="flex items-start justify-between">
        <div>
          {title && <h3 className="font-semibold">{title}</h3>}
          <p className="text-sm">{message}</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="ml-4 inline-flex text-lg leading-none opacity-60 hover:opacity-100"
          >
            ×
          </button>
        )}
      </div>
    </div>
  )
}

// Modal Component
export interface ModalProps {
  isOpen: boolean
  title: string
  children: React.ReactNode
  onClose: () => void
  actions?: React.ReactNode
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  title,
  children,
  onClose,
  actions,
}) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />
      <Card className="relative z-10 w-full max-w-md">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="text-2xl leading-none opacity-60 hover:opacity-100"
          >
            ×
          </button>
        </div>
        <div className="mb-4">{children}</div>
        {actions && <div className="flex gap-2 justify-end">{actions}</div>}
      </Card>
    </div>
  )
}

// Badge Component
export interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'success' | 'warning' | 'error'
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
}) => {
  const variantStyles = {
    default: 'bg-gray-100 text-gray-800',
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    error: 'bg-red-100 text-red-800',
  }

  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${variantStyles[variant]}`}>
      {children}
    </span>
  )
}

// Tabs Component
export interface TabsProps {
  tabs: Array<{ label: string; id: string }>
  activeTab: string
  onTabChange: (tabId: string) => void
}

export const Tabs: React.FC<TabsProps & { children: React.ReactNode }> = ({
  tabs,
  activeTab,
  onTabChange,
  children,
}) => (
  <div>
    <div className="border-b border-gray-200 flex gap-4">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`py-2 px-4 font-medium border-b-2 transition-colors ${
            activeTab === tab.id
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
    <div className="py-4">{children}</div>
  </div>
)
