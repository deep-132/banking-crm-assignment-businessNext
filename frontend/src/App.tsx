import { useCallback, useState } from 'react'
import { AlertCircle, Landmark, RotateCcw, Send } from 'lucide-react'
import { sendChatMessage } from './api/client'
import { ChatWindow } from './components/ChatWindow'
import type { ChatMessage } from './types/chat'

function createSessionId(): string {
  return `session-${Math.random().toString(36).slice(2)}-${performance.now().toString(36)}`
}

function getOrCreateSessionId(): string {
  const key = 'banking-crm-session-id'
  let id = localStorage.getItem(key)
  if (!id) {
    id = createSessionId()
    localStorage.setItem(key, id)
  }
  return id
}

function App() {
  const [sessionId, setSessionId] = useState(getOrCreateSessionId)
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

  const handleNewChat = () => {
    const id = createSessionId()
    localStorage.setItem('banking-crm-session-id', id)
    setSessionId(id)
    setMessages([])
    setError(null)
  }

  return (
    <div className="flex h-screen justify-center bg-linear-to-b from-slate-50 to-indigo-50/40 dark:from-slate-950 dark:to-indigo-950/20 sm:py-6">
      <div className="flex w-full max-w-4xl flex-col bg-white shadow-xl ring-1 ring-slate-200 dark:bg-slate-950 dark:ring-slate-800 sm:rounded-2xl">
        <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3.5 sm:px-6 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-linear-to-br from-indigo-500 to-violet-600 shadow-sm">
              <Landmark className="h-4.5 w-4.5 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-semibold leading-tight text-slate-900 dark:text-slate-100">
                RM Copilot
              </h1>
              <p className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
                </span>
                Personal loan outreach agent
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleNewChat}
            className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <RotateCcw className="h-3 w-3" />
            New chat
          </button>
        </header>

        <ChatWindow
          messages={messages}
          onExplain={handleExplain}
          explainingId={explainingId}
          loading={loading}
          onSuggestionClick={(text) => void runTurn(text, true)}
        />

        {error && (
          <div className="mx-4 mb-2 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 sm:mx-6 dark:bg-red-950/40 dark:text-red-300">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="border-t border-slate-200 p-3.5 sm:px-6 dark:border-slate-800">
          <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-1.5 py-1.5 pl-4 transition-colors focus-within:border-indigo-400 focus-within:bg-white dark:border-slate-700 dark:bg-slate-900 dark:focus-within:bg-slate-900">
            <input
              className="flex-1 bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400 dark:text-slate-100"
              placeholder="Ask the RM copilot…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              aria-label="Send"
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-indigo-500 to-violet-600 text-white shadow-sm transition-opacity hover:opacity-90 disabled:opacity-40"
              disabled={loading || !input.trim()}
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default App
