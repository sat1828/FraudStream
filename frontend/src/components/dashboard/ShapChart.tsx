'use client'

import { motion } from 'framer-motion'
import { BarChart2 } from 'lucide-react'

interface ShapFeature {
  feature_name: string
  value: number
  shap_value: number
  impact: 'positive' | 'negative'
}

interface Props {
  features: ShapFeature[]
  riskScore: number
  decision: string
}

const FEATURE_LABELS: Record<string, string> = {
  amount: 'Transaction Amount',
  amount_log: 'Log(Amount)',
  amount_velocity_5min: 'Amount Velocity 5m',
  amount_velocity_1h: 'Amount Velocity 1h',
  amount_velocity_24h: 'Amount Velocity 24h',
  txn_count_5min: 'Txn Count 5min',
  txn_count_1h: 'Txn Count 1h',
  txn_count_24h: 'Txn Count 24h',
  device_txn_count_1h: 'Device Txns 1h',
  device_txn_count_24h: 'Device Txns 24h',
  sender_unique_receivers_1h: 'Unique Receivers 1h',
  sender_unique_devices_24h: 'Unique Devices 24h',
  receiver_txn_count_1h: 'Receiver Txns 1h',
  is_new_device: 'New Device',
  is_new_receiver: 'New Receiver',
  is_night_txn: 'Night Transaction',
  is_festival_day: 'Festival Day',
  amount_zscore: 'Amount Z-Score',
  hour_of_day: 'Hour of Day',
  day_of_week: 'Day of Week',
}

export default function ShapWaterfallChart({ features, riskScore, decision }: Props) {
  const maxAbsShap = Math.max(...features.map(f => Math.abs(f.shap_value)), 0.001)
  const topN = features.slice(0, 8)

  const decisionColor = decision === 'BLOCK' ? 'var(--red-primary)'
    : decision === 'REVIEW' ? 'var(--amber-primary)'
    : 'var(--green-primary)'

  return (
    <div className="glass-card p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart2 size={15} style={{ color: 'var(--purple-primary)' }} />
          <span className="text-sm font-mono font-bold" style={{ color: 'var(--text-primary)' }}>SHAP EXPLANATION</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>RISK:</span>
          <span className="text-sm font-mono font-bold" style={{ color: decisionColor }}>
            {(riskScore * 100).toFixed(1)}%
          </span>
          <span className={`badge-${decision.toLowerCase()}`}>{decision}</span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mb-4">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm" style={{ background: 'var(--red-primary)' }} />
          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>Increases Risk</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm" style={{ background: 'var(--green-primary)' }} />
          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>Decreases Risk</span>
        </div>
      </div>

      {/* Waterfall bars */}
      <div className="space-y-2">
        {topN.map((feature, i) => {
          const pct = (Math.abs(feature.shap_value) / maxAbsShap) * 100
          const isPositive = feature.shap_value > 0
          const barColor = isPositive ? 'var(--red-primary)' : 'var(--green-primary)'
          const barGlow = isPositive ? 'rgba(255,45,85,0.3)' : 'rgba(0,255,157,0.3)'

          return (
            <motion.div
              key={feature.feature_name}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-center gap-3"
            >
              {/* Feature name */}
              <div className="w-36 text-right flex-shrink-0">
                <span className="text-xs font-mono truncate block" style={{ color: 'var(--text-secondary)' }}>
                  {FEATURE_LABELS[feature.feature_name] || feature.feature_name}
                </span>
              </div>

              {/* Center line + bar */}
              <div className="flex-1 relative h-5 flex items-center">
                {/* Center divider */}
                <div className="absolute left-1/2 w-px h-full" style={{ background: 'rgba(255,255,255,0.1)' }} />

                {/* Bar */}
                <div className={`absolute ${isPositive ? 'left-1/2' : 'right-1/2'} flex items-center h-4`}>
                  <motion.div
                    className="h-4 rounded-sm"
                    style={{
                      background: barColor,
                      boxShadow: `0 0 8px ${barGlow}`,
                      [isPositive ? 'marginLeft' : 'marginRight']: '0px',
                    }}
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.6, delay: i * 0.05, ease: 'easeOut' }}
                  />
                </div>
              </div>

              {/* SHAP value */}
              <div className="w-16 flex-shrink-0 text-right">
                <span className="text-xs font-mono font-bold" style={{ color: barColor }}>
                  {isPositive ? '+' : ''}{feature.shap_value.toFixed(3)}
                </span>
              </div>

              {/* Feature value */}
              <div className="w-14 flex-shrink-0">
                <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                  {typeof feature.value === 'number' ? feature.value.toFixed(2) : feature.value}
                </span>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Total risk score bar */}
      <div className="mt-4 pt-4" style={{ borderTop: '1px solid rgba(0,212,255,0.1)' }}>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-mono uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Final Risk Score</span>
          <span className="text-sm font-mono font-bold" style={{ color: decisionColor }}>{(riskScore * 100).toFixed(1)}%</span>
        </div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
          <motion.div
            className="h-full rounded-full"
            style={{
              background: `linear-gradient(90deg, var(--green-primary) 0%, var(--amber-primary) 40%, var(--red-primary) 80%)`,
              boxShadow: `0 0 8px ${decisionColor}`,
            }}
            initial={{ width: 0 }}
            animate={{ width: `${riskScore * 100}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        </div>
      </div>
    </div>
  )
}
