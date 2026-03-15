import { useEffect, useRef } from 'react'
import { useAppState } from './store/appStore'
import Dashboard from './components/Dashboard'

function App() {
  const { updateAnalysisData, symbol, price } = useAppState()
  const ws = useRef(null)

  useEffect(() => {
    // Connect to the FastAPI WebSocket endpoint
    ws.current = new WebSocket('ws://localhost:8000/ws/stream')

    ws.current.onopen = () => {
      console.log('Connected to Trading Hub Data Stream')
      ws.current.send(JSON.stringify({ type: 'subscribe', symbol: symbol, price: price }))
    }

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        // Ensure data exists before updating state
        if (data) {
          updateAnalysisData(data)
        }
      } catch (error) {
        console.error("Error parsing websocket data", error)
      }
    }

    ws.current.onerror = (error) => {
      console.error('WebSocket Error:', error)
    }

    ws.current.onclose = () => {
      console.log('Disconnected from Trading Hub Data Stream')
    }

    // Cleanup on unmount
    return () => {
      ws.current?.close()
    }
  }, [updateAnalysisData]) // Depend on updateAnalysisData

  // React to symbol and price changes and notify backend
  useEffect(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'subscribe', symbol: symbol, price: price }))
    }
  }, [symbol, price])

  return (
    <div className="min-h-screen bg-[#0f172a] text-[#f1f5f9] font-sans">
      <Dashboard />
    </div>
  )
}

export default App
