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
    <div className={`flex ${isRm ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] ${isRm ? 'items-end' : 'items-start'} flex flex-col gap-2`}>
        <div
          className={`whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isRm
              ? 'bg-indigo-600 text-white'
              : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100'
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
