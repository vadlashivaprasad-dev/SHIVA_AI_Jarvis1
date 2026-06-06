import React from 'react'

interface State {
  hasError: boolean
}

export class ErrorBoundary extends React.Component<React.PropsWithChildren, State> {
  state: State = {
    hasError: false,
  }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error('Application Error:', error, info)
  }

  handleReset = () => {
    // Hard reload is safest for client-side state recovery.
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-red-50">
          <div className="max-w-md w-full bg-white rounded-lg shadow p-6 space-y-4">
            <div>
              <h1 className="text-2xl font-bold">Something went wrong</h1>
              <p className="text-sm text-gray-600 mt-2">
                The UI crashed. Reloading restores a clean state.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={this.handleReset}
                className="flex-1 px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700"
              >
                Reload app
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

