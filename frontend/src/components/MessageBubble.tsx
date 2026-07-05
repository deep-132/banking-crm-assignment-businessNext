import { Bot, User } from 'lucide-react'
import type { ChatMessage } from '../types/chat'
import { CustomerCard } from './CustomerCard'

interface Props {
  message: ChatMessage
  onExplain: (customerId: string, customerName: string) => void
  explainingId: string | null
}

export function MessageBubble({ message, onExplain, explainingId }: Props) {
  const isRm = message.role === 'rm'

  return (
    <div className={`flex items-start gap-2.5 ${isRm ? 'flex-row-reverse' : ''}`}>
      <div
        className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
          isRm
            ? 'bg-indigo-600 text-white'
            : 'bg-linear-to-br from-emerald-500 to-teal-600 text-white'
        }`}
      >
        {isRm ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
      </div>

      <div className={`flex max-w-[85%] flex-col gap-2 ${isRm ? 'items-end' : 'items-start'}`}>
        <div
          className={`whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
            isRm
              ? 'rounded-tr-sm bg-indigo-600 text-white'
              : 'rounded-tl-sm bg-white text-slate-800 dark:bg-slate-800 dark:text-slate-100'
          }`}
        >
          {message.content}
        </div>

        {message.customers && message.customers.length > 0 && (
          <div className="grid w-full gap-2.5 sm:grid-cols-2">
            {message.customers.map((c) => (
              <CustomerCard
                key={c.customer_id}
                customer={c}
                onExplain={onExplain}
                explaining={explainingId === c.customer_id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
