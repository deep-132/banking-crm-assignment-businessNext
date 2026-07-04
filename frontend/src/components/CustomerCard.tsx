import { useState } from 'react'
import type { CustomerResult } from '../types/chat'

interface Props {
  customer: CustomerResult
  onExplain: (customerId: string, customerName: string) => void
  explaining: boolean
}

function ScoreBadge({ label, value, tone }: { label: string; value: number; tone: 'blue' | 'green' }) {
  const toneClasses =
    tone === 'blue'
      ? 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
      : 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${toneClasses}`}>
      {label} <span className="font-semibold">{value}</span>
    </span>
  )
}

export function CustomerCard({ customer, onExplain, explaining }: Props) {
  const [showMessage, setShowMessage] = useState(false)

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-slate-900 dark:text-slate-100">{customer.name}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {customer.customer_id} &middot; {customer.city} &middot; {customer.segment}
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-1.5">
          <ScoreBadge label="HVC" value={customer.hvc_score} tone="blue" />
          <ScoreBadge label="Conv" value={customer.conversion_score} tone="green" />
        </div>
      </div>

      {customer.recommended_product && (
        <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">
          Recommend <span className="font-medium">{customer.recommended_product}</span>
          {customer.recommended_amount != null &&
            ` — up to ₹${customer.recommended_amount.toLocaleString('en-IN')}`}
          {customer.recommended_rate != null && ` @ ${customer.recommended_rate}%`}
        </p>
      )}

      <div className="mt-3 flex gap-4 text-xs">
        <button
          type="button"
          className="font-medium text-indigo-600 hover:underline disabled:opacity-50 dark:text-indigo-400"
          onClick={() => onExplain(customer.customer_id, customer.name)}
          disabled={explaining}
        >
          {explaining ? 'Explaining…' : 'Why this customer?'}
        </button>
        {customer.whatsapp_message && (
          <button
            type="button"
            className="font-medium text-indigo-600 hover:underline dark:text-indigo-400"
            onClick={() => setShowMessage((v) => !v)}
          >
            {showMessage ? 'Hide WhatsApp draft' : 'View WhatsApp draft'}
          </button>
        )}
      </div>

      {showMessage && customer.whatsapp_message && (
        <div className="mt-2 rounded-lg bg-emerald-50 p-3 text-sm text-slate-800 dark:bg-emerald-950/40 dark:text-slate-200">
          {customer.whatsapp_message}
        </div>
      )}
    </div>
  )
}
