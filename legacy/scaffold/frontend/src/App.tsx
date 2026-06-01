import { useEffect, useState } from 'react'

export default function App() {
  const [health, setHealth] = useState<string>('loading...')

  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then((r) => r.json())
      .then((d) => setHealth(d.status))
      .catch(() => setHealth('error'))
  }, [])

  return (
    <div style={{ fontFamily: 'system-ui', padding: 24 }}>
      <h1>ShivaAI Jarvis</h1>
      <p>Backend health: <b>{health}</b></p>
    </div>
  )
}

