'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, Filter, RefreshCw, AlertTriangle, CheckCircle, Clock, ChevronLeft, ChevronRight } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { fetchTransactions } from '@/lib/api'
import { format } from 'date-fns'

const DECISION_FILTERS = ['ALL', 'ALLOW', 'BLOCK', 'REVIEW']

export default function TransactionsPage() {
  const [page, setPage] = useState(1)
  const [decision, setDecision] = useState('ALL')

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['transactions', page, decision],
    queryFn: () => fetchTransactions(page, decision === 'ALL' ? undefined : decision),
    refetchInterval: 5000,
  })

  const transactions = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / 50)

  return (
    <div className="p-6 space-y-5 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold" style={{ fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>
            TRANSACTION LOG
          </h1>
          <p className="text-xs font-mono mt-0.5" style={{ color: 'var(--text-muted)' }}>
            All transactions with ML predictions — {total.toLocaleString()} total
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="glass-button flex items-center gap-1.5 px-3 py-1.5 text-xs"
          >
            <motion.div animate={isFetching ? { rotate: 360 } : { rotate: 0 }} transition={{ duration: 0.8, repeat: isFetching ? Infinity : 0, ease: 'linear' }}>
              <RefreshCw size={12} />
            </motion.div>
            REFRESH
          </button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2">
        <Filter size={13} style={{ color: 'var(--text-muted)' }} />
        <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>FILTER:</span>
        {DECISION_FILTERS.map(f => (
          <motion.button
            key={f}
            onClick={() => { setDecision(f); setPage(1) }}
            className="px-3 py-1 rounded text-xs font-mono transition-colors"
            style={{
              background: decision === f ? 'rgba(0,212,255,0.15)' : 'rgba(0,212,255,0.04)',
              border: `1px solid ${decision === f ? 'rgba(0,212,255,0.4)' : 'rgba(0,212,255,0.12)'}`,
              color: decision === f ? 'var(--cyan-primary)' : 'var(--text-muted)',
            }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {f}
          </motion.button>
        ))}
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="cyber-table">
            <thead>
              <tr>
                <th>TXN ID</th>
                <th>SENDER VPA</th>
                <th>RECEIVER VPA</th>
                <th>AMOUNT (₹)</th>
                <th>CITY</th>
                <th>DECISION</th>
                <th>RISK SCORE</th>
                <th>LATENCY</th>
                <th>TIMESTAMP</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={9} className="text-center py-10 text-sm font-mono" style={{ color: 'var(--text-muted)' }}>
                  <div className="flex items-center justify-center gap-2">
                    <motion.div className="w-4 h-4 border-2 rounded-full" style={{ borderColor: 'rgba(0,212,255,0.2)', borderTopColor: 'var(--cyan-primary)' }} animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }} />
                    Loading transactions...
                  </div>
                </td></tr>
              ) : transactions.length === 0 ? (
                <tr><td colSpan={9} className="text-center py-10 text-sm font-mono" style={{ color: 'var(--text-muted)' }}>No transactions found</td></tr>
              ) : (
                <AnimatePresence>
                  {transactions.map((tx: any, i: number) => (
                    <motion.tr
                      key={tx.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.01 }}
                    >
                      <td className="font-mono text-xs" style={{ color: 'var(--cyan-primary)' }}>
                        {tx.transaction_id.slice(-10)}
                      </td>
                      <td className="font-mono text-xs max-w-[120px]">
                        <div className="truncate" style={{ color: 'var(--text-secondary)' }}>{tx.sender_vpa}</div>
                      </td>
                      <td className="font-mono text-xs max-w-[120px]">
                        <div className="truncate" style={{ color: 'var(--text-secondary)' }}>{tx.receiver_vpa}</div>
                      </td>
                      <td className="font-mono text-xs font-bold" style={{ color: 'var(--text-primary)' }}>
                        {tx.amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </td>
                      <td className="font-mono text-xs" style={{ color: 'var(--text-muted)' }}>{tx.city}</td>
                      <td>
                        {tx.decision === 'BLOCK' ? (
                          <span className="badge-block flex items-center gap-1 w-fit">
                            <AlertTriangle size={10} />BLOCK
                          </span>
                        ) : tx.decision === 'REVIEW' ? (
                          <span className="badge-review flex items-center gap-1 w-fit">
                            <Clock size={10} />REVIEW
                          </span>
                        ) : (
                          <span className="badge-allow flex items-center gap-1 w-fit">
                            <CheckCircle size={10} />ALLOW
                          </span>
                        )}
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${(tx.risk_score ?? 0) * 100}%`,
                                background: (tx.risk_score ?? 0) >= 0.5 ? 'var(--red-primary)' : (tx.risk_score ?? 0) >= 0.3 ? 'var(--amber-primary)' : 'var(--green-primary)',
                              }}
                            />
                          </div>
                          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                            {((tx.risk_score ?? 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                      <td className="font-mono text-xs" style={{ color: 'var(--text-muted)' }}>
                        {tx.inference_latency_ms ? `${tx.inference_latency_ms.toFixed(1)}ms` : '—'}
                      </td>
                      <td className="font-mono text-xs" style={{ color: 'var(--text-muted)' }}>
                        {format(new Date(tx.initiated_at), 'HH:mm:ss dd/MM')}
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3" style={{ borderTop: '1px solid rgba(0,212,255,0.08)' }}>
            <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
              Page {page} of {totalPages} • {total.toLocaleString()} records
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="glass-button p-1.5 disabled:opacity-30"
              >
                <ChevronLeft size={14} />
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="glass-button p-1.5 disabled:opacity-30"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
