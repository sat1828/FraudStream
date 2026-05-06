'use client'

import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, RefreshCw, X, CheckCircle2 } from 'lucide-react'
import confetti from 'canvas-confetti'

interface DriftAlert {
  drift_score: number
  threshold: number
  report_id: string
  message: string
  severity: 'high' | 'medium'
  retrained?: boolean
}

interface Props {
  alert: DriftAlert | null
  onDismiss: () => void
}

export default function DriftAlertBanner({ alert, onDismiss }: Props) {
  const confettiFired = useRef(false)

  useEffect(() => {
    if (alert?.retrained && !confettiFired.current) {
      confettiFired.current = true
      // Cyber-themed confetti
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.15 },
        colors: ['#00d4ff', '#a855f7', '#00ff9d', '#ffffff'],
        shapes: ['circle', 'square'],
        scalar: 0.8,
      })
    }
    if (!alert) confettiFired.current = false
  }, [alert?.retrained])

  return (
    <AnimatePresence>
      {alert && (
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -10, scale: 0.98 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          className="relative overflow-hidden rounded-xl"
          style={{
            background: alert.retrained
              ? 'linear-gradient(135deg, rgba(0,255,157,0.1), rgba(0,212,255,0.08))'
              : 'linear-gradient(135deg, rgba(255,45,85,0.12), rgba(255,184,0,0.08))',
            border: `1px solid ${alert.retrained ? 'rgba(0,255,157,0.3)' : alert.severity === 'high' ? 'rgba(255,45,85,0.4)' : 'rgba(255,184,0,0.4)'}`,
            backdropFilter: 'blur(20px)',
          }}
        >
          {/* Animated scan line */}
          {!alert.retrained && (
            <motion.div
              className="absolute inset-x-0 h-px"
              style={{ background: 'linear-gradient(90deg, transparent, rgba(255,45,85,0.6), transparent)' }}
              animate={{ top: ['0%', '100%'] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            />
          )}

          <div className="flex items-start gap-3 p-4">
            {/* Icon */}
            <div className={`flex-shrink-0 mt-0.5 ${!alert.retrained ? 'animate-pulse-red' : ''}`}>
              {alert.retrained ? (
                <CheckCircle2 size={20} style={{ color: 'var(--green-primary)' }} />
              ) : (
                <AlertTriangle size={20} style={{ color: alert.severity === 'high' ? 'var(--red-primary)' : 'var(--amber-primary)' }} />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-bold font-mono" style={{
                  color: alert.retrained ? 'var(--green-primary)' : alert.severity === 'high' ? 'var(--red-primary)' : 'var(--amber-primary)'
                }}>
                  {alert.retrained ? '✓ MODEL RETRAINED' : '⚡ CONCEPT DRIFT DETECTED'}
                </span>
                <span className="text-xs font-mono px-2 py-0.5 rounded" style={{
                  background: `rgba(${alert.severity === 'high' ? '255,45,85' : '255,184,0'},0.1)`,
                  color: alert.severity === 'high' ? 'var(--red-primary)' : 'var(--amber-primary)',
                  border: `1px solid rgba(${alert.severity === 'high' ? '255,45,85' : '255,184,0'},0.2)`
                }}>
                  {alert.severity.toUpperCase()}
                </span>
              </div>
              <p className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                {alert.message}
              </p>
              <div className="flex items-center gap-4 mt-2">
                <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                  Drift Score: <span style={{ color: 'var(--amber-primary)', fontWeight: 700 }}>{(alert.drift_score * 100).toFixed(1)}%</span>
                </span>
                <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                  Threshold: {(alert.threshold * 100).toFixed(0)}%
                </span>
                {!alert.retrained && (
                  <span className="flex items-center gap-1 text-xs font-mono" style={{ color: 'var(--cyan-primary)' }}>
                    <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}>
                      <RefreshCw size={11} />
                    </motion.div>
                    Retraining model...
                  </span>
                )}
              </div>
            </div>

            {/* Dismiss */}
            <button
              onClick={onDismiss}
              className="flex-shrink-0 p-1 rounded hover:bg-white/10 transition-colors"
              style={{ color: 'var(--text-muted)' }}
            >
              <X size={14} />
            </button>
          </div>

          {/* Drift score progress bar */}
          <div className="px-4 pb-3">
            <div className="flex justify-between text-xs font-mono mb-1" style={{ color: 'var(--text-muted)' }}>
              <span>DRIFT LEVEL</span>
              <span>{(alert.drift_score * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
              <motion.div
                className="h-full rounded-full"
                style={{
                  background: alert.retrained
                    ? 'linear-gradient(90deg, var(--green-primary), var(--cyan-primary))'
                    : 'linear-gradient(90deg, var(--amber-primary), var(--red-primary))',
                }}
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(alert.drift_score * 100, 100)}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
