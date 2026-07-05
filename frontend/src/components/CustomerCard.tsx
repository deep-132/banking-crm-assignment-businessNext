import { useState } from 'react'
import { HelpCircle, MessageCircle, Sparkles } from 'lucide-react'
import type { CustomerResult } from '../types/chat'

interface Props {
  customer: CustomerResult
  onExplain: (customerId: string, customerName: string) => void
  explaining: boolean
}

const SEGMENT_STYLES: Record<string, string> = {
  HNI: 'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
  'Mass Affluent': 'bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300',
  Retail: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
}

function tierClasses(value: number): string {
  if (value >= 80) return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
  if (value >= 50) return 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
  return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
}

function tierBarColor(value: number): string {
  if (value >= 80) return 'bg-emerald-500'
  if (value >= 50) return 'bg-amber-500'
  return 'bg-slate-400'
}

function initials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')
}

function ScoreMeter({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex-1">
      <div className="mb-1 flex items-center justify-between text-[11px] font-medium text-slate-500 dark:text-slate-400">
        <span>{label}</span>
        <span className={`rounded px-1.5 py-0.5 ${tierClasses(value)}`}>{value}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div
          className={`h-full rounded-full ${tierBarColor(value)} transition-all`}
          style={{ width: `${Math.min(100, Math.max(4, value))}%` }}
        />
      </div>
    </div>
  )
}

export function CustomerCard({ customer, onExplain, explaining }: Props) {
  const [showMessage, setShowMessage] = useState(false)
  const segmentClass = SEGMENT_STYLES[customer.segment] ?? SEGMENT_STYLES.Retail

  return (
    <div className="group rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-indigo-500 to-violet-600 text-sm font-semibold text-white">
          {initials(customer.name)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <p className="truncate font-semibold text-slate-900 dark:text-slate-100">{customer.name}</p>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${segmentClass}`}>
              {customer.segment}
            </span>
          </div>
          <p className="truncate text-xs text-slate-500 dark:text-slate-400">
            {customer.customer_id} &middot; {customer.city}
          </p>
        </div>
      </div>

      <div className="mt-3 flex gap-3">
        <ScoreMeter label="High-value" value={customer.hvc_score} />
        <ScoreMeter label="Conversion" value={customer.conversion_score} />
      </div>

      {customer.recommended_product && (
        <div className="mt-3 flex items-start gap-2 rounded-xl bg-indigo-50 px-3 py-2 text-sm text-indigo-900 dark:bg-indigo-950/50 dark:text-indigo-200">
          <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-indigo-500 dark:text-indigo-400" />
          <p>
            <span className="font-medium">{customer.recommended_product}</span>
            {customer.recommended_amount != null &&
              ` — up to ₹${customer.recommended_amount.toLocaleString('en-IN')}`}
            {customer.recommended_rate != null && ` @ ${customer.recommended_rate}%`}
          </p>
        </div>
      )}

      <div className="mt-3 flex items-center gap-3 border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
        <button
          type="button"
          className="inline-flex items-center gap-1 font-medium text-slate-600 hover:text-indigo-600 disabled:opacity-50 dark:text-slate-400 dark:hover:text-indigo-400"
          onClick={() => onExplain(customer.customer_id, customer.name)}
          disabled={explaining}
        >
          <HelpCircle className="h-3.5 w-3.5" />
          {explaining ? 'Explaining…' : 'Why this customer?'}
        </button>
        {customer.whatsapp_message && (
          <button
            type="button"
            className="inline-flex items-center gap-1 font-medium text-slate-600 hover:text-emerald-600 dark:text-slate-400 dark:hover:text-emerald-400"
            onClick={() => setShowMessage((v) => !v)}
          >
            <MessageCircle className="h-3.5 w-3.5" />
            {showMessage ? 'Hide draft' : 'WhatsApp draft'}
          </button>
        )}
      </div>

      {showMessage && customer.whatsapp_message && (
        <div className="mt-2 rounded-xl rounded-tl-sm bg-emerald-50 p-3 text-sm leading-relaxed text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100">
          <div className="mb-1 flex items-center gap-1.5 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
            <MessageCircle className="h-3 w-3" /> WhatsApp draft
          </div>
          {customer.whatsapp_message}
        </div>
      )}
    </div>
  )
}
