import { useEffect, useRef } from 'react'
import { Bot, Sparkles } from 'lucide-react'
import type { ChatMessage } from '../types/chat'
import { MessageBubble } from './MessageBubble'

interface Props {
  messages: ChatMessage[]
  onExplain: (customerId: string, customerName: string) => void
  explainingId: string | null
  loading: boolean
  onSuggestionClick: (text: string) => void
}

const SUGGESTIONS = [
  'Find high-value customers likely to convert for a personal loan this month and generate personalized WhatsApp messages',
  'Just show me the top 5 in Mumbai',
  'Only show HNI customers',
]

export function ChatWindow({ messages, onExplain, explainingId, loading, onSuggestionClick }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  return (
    <div className="flex-1 space-y-5 overflow-y-auto px-4 py-6 sm:px-8">
      {messages.length === 0 && (
        <div className="mx-auto flex max-w-md flex-col items-center gap-4 rounded-2xl border border-dashed border-slate-300 bg-white/60 p-8 text-center dark:border-slate-700 dark:bg-slate-900/40">
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-linear-to-br from-indigo-500 to-violet-600">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Ask me to find, rank, or explain customers for a lending campaign.
          </p>
          <div className="flex flex-col gap-2 w-full">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onSuggestionClick(s)}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-xs text-slate-600 shadow-sm transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-indigo-950/40"
              >
                <Sparkles className="h-3.5 w-3.5 shrink-0 text-indigo-400" />
                {s}
              </button>
            ))}
          </div>
        </div>
      )}
      {messages.map((m, i) => (
        <MessageBubble key={i} message={m} onExplain={onExplain} explainingId={explainingId} />
      ))}
      {loading && (
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-emerald-500 to-teal-600">
            <Bot className="h-3.5 w-3.5 text-white" />
          </div>
          <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm bg-white px-4 py-3 shadow-sm dark:bg-slate-800">
            <span className="typing-dot h-1.5 w-1.5 rounded-full bg-slate-400" style={{ animationDelay: '0ms' }} />
            <span className="typing-dot h-1.5 w-1.5 rounded-full bg-slate-400" style={{ animationDelay: '150ms' }} />
            <span className="typing-dot h-1.5 w-1.5 rounded-full bg-slate-400" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
