import { useEffect, useRef } from 'react'
import type { ChatMessage } from '../types/chat'
import { MessageBubble } from './MessageBubble'

interface Props {
  messages: ChatMessage[]
  onExplain: (customerId: string, customerName: string) => void
  explainingId: string | null
  loading: boolean
}

export function ChatWindow({ messages, onExplain, explainingId, loading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  return (
    <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6 sm:px-8">
      {messages.length === 0 && (
        <div className="mx-auto max-w-md rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
          Try: "Find high-value customers likely to convert for a personal loan this month and
          generate personalized WhatsApp messages."
        </div>
      )}
      {messages.map((m, i) => (
        <MessageBubble key={i} message={m} onExplain={onExplain} explainingId={explainingId} />
      ))}
      {loading && (
        <div className="flex justify-start">
          <div className="animate-pulse rounded-2xl bg-slate-100 px-4 py-2.5 text-sm text-slate-500 dark:bg-slate-800 dark:text-slate-400">
            Thinking…
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
