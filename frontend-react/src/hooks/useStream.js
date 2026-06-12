/**
 * useStream — SSE consumer hook.
 *
 * Connects once to /api/stream and updates state as events arrive.
 * No polling loop. When isRunning flips false, connection stays open
 * so we receive the final status update.
 */
import { useEffect, useRef, useState } from 'react'

const DEFAULT_STATE = {
  isRunning: false,
  pid: null,
  telemetry: {},
  logs: [],
  preview: null,
  isLive: false,
  connected: false,
}

export function useStream() {
  const [state, setState] = useState(DEFAULT_STATE)
  const esRef = useRef(null)

  useEffect(() => {
    function connect() {
      if (esRef.current) esRef.current.close()

      const es = new EventSource('/api/stream')
      esRef.current = es

      es.onopen = () => setState(s => ({ ...s, connected: true }))

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          setState({
            isRunning: data.is_running,
            pid: data.pid,
            telemetry: data.telemetry || {},
            logs: data.logs || [],
            preview: data.preview,
            isLive: data.is_live,
            connected: true,
          })
        } catch { /* ignore parse errors */ }
      }

      es.onerror = () => {
        setState(s => ({ ...s, connected: false }))
        es.close()
        // Reconnect after 3s if connection drops
        setTimeout(connect, 3000)
      }
    }

    connect()
    return () => esRef.current?.close()
  }, [])

  return state
}
