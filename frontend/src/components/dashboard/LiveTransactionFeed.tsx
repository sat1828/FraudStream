'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, AlertTriangle, CheckCircle, Clock, Wifi, WifiOff } from 'lucide-react'
import { format } from 'date-fns'

import { useAuthStore } from '@/lib/auth-store'

const getWsUrl = (token: string | null) => {
  if (typeof window === 'undefined') return ''
  const base = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
  const param = token ? `?token=${encodeURIComponent(token)}` : ''
  return `${base}/ws/live${param}`
}

interface LiveTransaction {
  transaction_id: string
  sender_vpa: string
  receiver_vpa: string
  amount: number
  city: string
  decision: 'ALLOW' | 'BLOCK' | 'REVIEW'
  risk_score: number
  latency_ms: number
  top_feature: string
  rule_triggers: string[]
  model_version: string
  timestamp: string
}

interface WSEvent {
  event_type: string
  payload: any
  timestamp: string
}

const MAX_FEED_SIZE = 100

export function useLiveFeed(onDriftAlert?: (payload: any) => void) {
  const [transactions, setTransactions] = useState<LiveTransaction[]>([])
  const [connected, setConnected] = useState(false)
  const [connectionAttempts, setConnectionAttempts] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { token } = useAuthStore()

  const connect = useCallback(() => {
    const url = getWsUrl(token)
    if (!url || wsRef.current?.readyState === WebSocket.OPEN) return

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setConnectionAttempts(0)
        // Keep-alive ping
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('ping')
        }, 30000)
        ws.addEventListener('close', () => clearInterval(pingInterval))
      }

      ws.onmessage = (event) => {
        try {
          const msg: WSEvent = JSON.parse(event.data)
          if (msg.event_type === 'transaction') {
            const tx: LiveTransaction = {
              ...msg.payload,
              timestamp: msg.timestamp,
            }
            setTransactions(prev => [tx, ...prev].slice(0, MAX_FEED_SIZE))
          } else if (msg.event_type === 'drift_alert' && onDriftAlert) {
            onDriftAlert(msg.payload)
          }
        } catch {}
      }

      ws.onclose = () => {
        setConnected(false)
        wsRef.current = null
        const delay = Math.min(1000 * Math.pow(1.5, connectionAttempts), 10000)
        reconnectTimer.current = setTimeout(() => {
          setConnectionAttempts(a => a + 1)
          connect()
        }, delay)
      }

      ws.onerror = () => ws.close()
    } catch {}
  }, [token, connectionAttempts, onDriftAlert])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { transactions, connected }
}

const DECISION_CONFIG = {
  ALLOW: { label: 'ALLOW', className: 'badge-allow', icon: CheckCircle, iconColor: 'var(--green-primary)' },
  BLOCK: { label: 'BLOCK', className: 'badge-block', icon: AlertTriangle, iconColor: 'var(--red-primary)' },
  REVIEW: { label: 'REVIEW', className: 'badge-review', icon: Clock, iconColor: 'var(--amber-primary)' },
}

function RiskBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = score >= 0.5 ? 'var(--red-primary)' : score >= 0.3 ? 'var(--amber-primary)' : 'var(--green-primary)'
  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: color, boxShadow: `0 0 6px ${color}` }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4 }}
        />
      </div>
      <span className="text-xs font-mono w-8 text-right" style={{ color }}>
        {pct}%
      </span>
    </div>
  )
}

function TransactionRow({ tx, index }: { tx: LiveTransaction; index: number }) {
  const config = DECISION_CONFIG[tx.decision] ?? DECISION_CONFIG.ALLOW
  const Icon = config.icon

  return (
    <motion.tr
      initial={{ opacity: 0, x: 20, backgroundColor: 'rgba(0,212,255,0.05)' }}
      animate={{ opacity: 1, x: 0, backgroundColor: 'transparent' }}
      transition={{ duration: 0.35, delay: index === 0 ? 0 : 0 }}
      layout
    >
      <td className="font-mono text-xs" style={{ color: 'var(--cyan-primary)', paddingLeft: '16px', paddingRight: '8px', paddingTop: '10px', paddingBottom: '10px' }}>
        {tx.transaction_id.slice(-8)}
      </td>
      <td className="font-mono text-xs" style={{ color: 'var(--text-secondary)', maxWidth: '120px' }}>
        <div className="truncate">{tx.sender_vpa}</div>
      </td>
      <td className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>
        ₹{tx.amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
      </td>
      <td>
        <div className="flex items-center gap-1.5">
          <Icon size={12} style={{ color: config.iconColor, flexShrink: 0 }} />
          <span className={config.className}>{config.label}</span>
        </div>
      </td>
      <td>
        <RiskBar score={tx.risk_score} />
      </td>
      <td className="font-mono text-xs" style={{ color: 'var(--text-muted)' }}>
        {tx.latency_ms?.toFixed(1)}ms
      </td>
      <td className="font-mono text-xs" style={{ color: 'var(--text-muted)', paddingRight: '16px' }}>
        {tx.city}
      </td>
    </motion.tr>
  )
}

export default function LiveTransactionFeed({ onDriftAlert }: { onDriftAlert?: (p: any) => void }) {
  const { transactions, connected } = useLiveFeed(onDriftAlert)

  return (
    <div className="glass-card overflow-hidden flex flex-col" style={{ maxHeight: '460px' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid rgba(0,212,255,0.1)' }}>
        <div className="flex items-center gap-2">
          <Activity size={15} style={{ color: 'var(--cyan-primary)' }} />
          <span className="text-sm font-mono font-bold" style={{ color: 'var(--text-primary)' }}>LIVE TRANSACTION STREAM</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            {connected ? (
              <><div className="live-dot" /><span className="text-xs font-mono" style={{ color: 'var(--green-primary)' }}>STREAMING</span></>
            ) : (
              <><WifiOff size={12} style={{ color: 'var(--red-primary)' }} /><span className="text-xs font-mono" style={{ color: 'var(--red-primary)' }}>RECONNECTING</span></>
            )}
          </div>
          <span className="text-xs font-mono px-2 py-0.5 rounded" style={{ background: 'rgba(0,212,255,0.08)', color: 'var(--text-muted)' }}>
            {transactions.length} / {MAX_FEED_SIZE}
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-y-auto flex-1">
        <table className="cyber-table">
          <thead className="sticky top-0" style={{ background: 'rgba(4,13,24,0.95)', zIndex: 10 }}>
            <tr>
              <th>TXN ID</th>
              <th>SENDER VPA</th>
              <th>AMOUNT</th>
              <th>DECISION</th>
              <th>RISK SCORE</th>
              <th>LATENCY</th>
              <th>CITY</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {transactions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-sm font-mono" style={{ color: 'var(--text-muted)' }}>
                    {connected ? (
                      <span className="flex items-center justify-center gap-2">
                        <motion.div
                          className="w-4 h-4 border-2 rounded-full"
                          style={{ borderColor: 'rgba(0,212,255,0.2)', borderTopColor: 'var(--cyan-primary)' }}
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        />
                        Awaiting transactions...
                      </span>
                    ) : (
                      'Connecting to stream...'
                    )}
                  </td>
                </tr>
              ) : (
                transactions.map((tx, i) => (
                  <TransactionRow key={tx.transaction_id} tx={tx} index={i} />
                ))
              )}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </div>
  )
}
