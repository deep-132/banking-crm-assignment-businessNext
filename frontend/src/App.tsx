import { useCallback, useState } from 'react'
import { sendChatMessage } from './api/client'
import { ChatWindow } from './components/ChatWindow'
import type { ChatMessage } from './types/chat'

function getOrCreateSessionId(): string {
  const key = 'banking-crm-session-id'
  let id = localStorage.getItem(key)
  if (!id) {
    id = `session-${Math.random().toString(36).slice(2)}-${performance.now().toString(36)}`
    localStorage.setItem(key, id)
  }
  return id
}

function App() {
  const [sessionId] = useState(getOrCreateSessionId)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [explainingId, setExplainingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const runTurn = useCallback(
    async (text: string, displayAsRmMessage: boolean) => {
      setError(null)
      if (displayAsRmMessage) {
        setMessages((prev) => [...prev, { role: 'rm', content: text }])
      }
      setLoading(true)
      try {
        const res = await sendChatMessage(sessionId, text)
        setMessages((prev) => [
          ...prev,
          { role: 'agent', content: res.reply_text, customers: res.customers, action: res.action },
        ])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Something went wrong contacting the agent.')
      } finally {
        setLoading(false)
      }
    },
    [sessionId],
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    void runTurn(text, true)
  }

  const handleExplain = useCallback(
    (customerId: string, customerName: string) => {
      setExplainingId(customerId)
      void runTurn(`Why was ${customerName} (${customerId}) picked?`, true).finally(() =>
        setExplainingId(null),
      )
    },
    [runTurn],
  )

  return (
    <div className="mx-auto flex h-screen max-w-4xl flex-col bg-white dark:bg-slate-950">
      <header className="border-b border-slate-200 px-4 py-4 sm:px-8 dark:border-slate-800">
        <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          RM Copilot — Personal Loan Outreach
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Agentic CRM assistant · session {sessionId.slice(0, 18)}…
        </p>
      </header>

      <ChatWindow messages={messages} onExplain={handleExplain} explainingId={explainingId} loading={loading} />

      {error && (
        <div className="mx-4 mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 sm:mx-8 dark:bg-red-950/40 dark:text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="border-t border-slate-200 p-4 sm:px-8 dark:border-slate-800">
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-full border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            placeholder="Ask the RM copilot…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="rounded-full bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            disabled={loading || !input.trim()}
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}

export default App
