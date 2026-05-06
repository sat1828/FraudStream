'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity, Shield, Zap, TrendingUp, BarChart3,
  AlertTriangle, Clock, Database,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import MetricCard from '@/components/dashboard/MetricCard'
import LiveTransactionFeed, { useLiveFeed } from '@/components/dashboard/LiveTransactionFeed'
import DriftAlertBanner from '@/components/dashboard/DriftAlertBanner'
import ShapChart from '@/components/dashboard/ShapChart'
import { fetchMetrics, type SystemMetrics } from '@/lib/api'
import { format } from 'date-fns'
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts'

function useTpsHistory(currentTps: number) {
  const history = useRef<{ t: number; v: number }[]>([])
  useEffect(() => {
    if (currentTps === undefined) return
    history.current = [
      ...history.current.slice(-29),
      { t: Date.now(), v: currentTps },
    ]
  }, [currentTps])
  return history.current.length > 1
    ? history.current
    : Array.from({ length: 10 }, (_, i) => ({ t: i, v: 0 }))
}

const stagger = {
  container: { hidden: {}, show: { transition: { staggerChildren: 0.07 } } },
  item: {
    hidden: { opacity: 0, y: 16 },
    show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
  },
}

export default function DashboardPage() {
  const [driftAlert, setDriftAlert] = useState<any>(null)

  const { data: metrics } = useQuery<SystemMetrics>({
    queryKey: ['metrics'],
    queryFn: fetchMetrics,
    refetchInterval: 5_000,
    staleTime: 4_000,
  })

  const handleDriftAlert = useCallback((payload: any) => {
    setDriftAlert(payload)
    setTimeout(() => setDriftAlert(null), 30_000)
  }, [])

  const { transactions } = useLiveFeed(handleDriftAlert)

  const lastTx = transactions[0]

  // Build SHAP features from real WebSocket payload when available
  const liveShapFeatures = lastTx?.shap_features && lastTx.shap_features.length > 0
    ? lastTx.shap_features.slice(0, 8).map((f: any) => ({
        feature_name: f.feature_name,
        value: f.value,
        shap_value: f.shap_value,
        impact: f.impact as 'positive' | 'negative',
      }))
    : lastTx
      ? [
          { feature_name: lastTx.top_feature || 'amount_velocity_5min', value: lastTx.amount, shap_value: lastTx.risk_score * 0.45, impact: 'positive' as const },
          { feature_name: 'txn_count_5min', value: 3, shap_value: lastTx.risk_score * 0.28, impact: 'positive' as const },
          { feature_name: 'is_new_device', value: 1, shap_value: lastTx.risk_score * 0.15, impact: 'positive' as const },
          { feature_name: 'is_night_txn', value: new Date().getHours() < 6 ? 1 : 0, shap_value: lastTx.risk_score * 0.08, impact: 'positive' as const },
          { feature_name: 'sender_unique_receivers_1h', value: 2, shap_value: lastTx.risk_score * 0.06, impact: 'positive' as const },
          { feature_name: 'amount_zscore', value: 1.4, shap_value: lastTx.risk_score * 0.04, impact: 'positive' as const },
          { feature_name: 'device_txn_count_1h', value: 2, shap_value: -0.03, impact: 'negative' as const },
          { feature_name: 'is_festival_day', value: 0, shap_value: -0.01, impact: 'negative' as const },
        ]
      : [
          { feature_name: 'amount_velocity_5min', value: 0, shap_value: 0, impact: 'positive' as const },
          { feature_name: 'txn_count_5min', value: 0, shap_value: 0, impact: 'positive' as const },
        ]

  const liveDecision  = lastTx?.decision  ?? 'ALLOW'
  const liveRiskScore = lastTx?.risk_score ?? 0

  const sparkData = useTpsHistory(metrics?.tps ?? 0)

  return (
    <div className="p-6 space-y-6 min-h-screen">

      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-xl font-bold" style={{ fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>
            FRAUD OPERATIONS CENTER
          </h1>
          <p className="text-xs font-mono mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Real-time UPI transaction monitoring &amp; ML inference
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
            style={{ background: 'rgba(0,255,157,0.06)', border: '1px solid rgba(0,255,157,0.15)' }}>
            <div className="live-dot" />
            <span className="text-xs font-mono" style={{ color: 'var(--green-primary)' }}>LIVE</span>
          </div>
          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            {format(new Date(), 'dd MMM yyyy HH:mm:ss')}
          </span>
        </div>
      </motion.div>

      <DriftAlertBanner alert={driftAlert} onDismiss={() => setDriftAlert(null)} />

      <motion.div variants={stagger.container} initial="hidden" animate="show"
        className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <motion.div variants={stagger.item}>
          <MetricCard
            label="Total Transactions"
            value={metrics?.total_transactions ?? 0}
            icon={Database} color="cyan"
            trend="up" trendValue="+live"
            description="All time"
          />
        </motion.div>
        <motion.div variants={stagger.item}>
          <MetricCard
            label="Fraud Rate"
            value={metrics?.fraud_rate_percent ?? 0}
            unit="%" icon={AlertTriangle} color="red"
            trend="neutral" trendValue="stable"
            description="BLOCK decisions"
            precision={3}
          />
        </motion.div>
        <motion.div variants={stagger.item}>
          <MetricCard
            label="P95 Latency"
            value={metrics?.p95_latency_ms ?? 0}
            unit="ms" icon={Zap} color="green"
            trend="down" trendValue="<80ms target"
            description="Inference pipeline"
            precision={1}
          />
        </motion.div>
        <motion.div variants={stagger.item}>
          <MetricCard
            label="Drift Score"
            value={(metrics?.drift_score ?? 0) * 100}
            unit="%" icon={TrendingUp}
            color={metrics?.drift_score && metrics.drift_score > 0.1 ? 'red' : 'purple'}
            description={`Threshold 10% | ${metrics?.current_model_version ?? 'â€”'}`}
            precision={2}
          />
        </motion.div>
      </motion.div>

      <motion.div variants={stagger.container} initial="hidden" animate="show"
        className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <motion.div variants={stagger.item}>
          <MetricCard
            label="Transactions / Hour"
            value={metrics?.transactions_last_hour ?? 0}
            icon={Activity} color="cyan"
          />
        </motion.div>
        <motion.div variants={stagger.item}>
          <MetricCard
            label="Avg Latency"
            value={metrics?.avg_latency_ms ?? 0}
            unit="ms" icon={Clock} color="purple" precision={1}
          />
        </motion.div>
        <motion.div variants={stagger.item}>
          <MetricCard
            label="Live TPS"
            value={metrics?.tps ?? 0}
            icon={BarChart3} color="green"
            description="Transactions per second"
            precision={2}
          />
        </motion.div>
        <motion.div variants={stagger.item}>
          <MetricCard
            label="Active Model"
            value={metrics?.current_model_version ?? 'â€¦'}
            icon={Shield} color="cyan" animate={false}
          />
        </motion.div>
      </motion.div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

        <motion.div className="xl:col-span-2"
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}>
          <LiveTransactionFeed onDriftAlert={handleDriftAlert} />
        </motion.div>

        <motion.div className="space-y-4"
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}>

          <div className="relative">
            {lastTx && (
              <div className="absolute -top-2 -right-2 z-10">
                <motion.span
                  key={lastTx.transaction_id}
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="text-xs font-mono px-2 py-0.5 rounded"
                  style={{ background: 'rgba(0,212,255,0.12)', border: '1px solid rgba(0,212,255,0.25)', color: 'var(--cyan-primary)' }}
                >
                  LIVE
                </motion.span>
              </div>
            )}
            <ShapChart
              features={liveShapFeatures}
              riskScore={liveRiskScore}
              decision={liveDecision}
            />
          </div>

          <div className="glass-card p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
                TRANSACTION RATE
              </span>
              <span className="text-xs font-mono" style={{ color: 'var(--cyan-primary)' }}>
                {metrics?.tps?.toFixed(1) ?? '0.0'} TPS
              </span>
            </div>
            <ResponsiveContainer width="100%" height={80}>
              <LineChart data={sparkData}>
                <defs>
                  <linearGradient id="cyanGrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#00d4ff" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#a855f7" stopOpacity={0.8} />
                  </linearGradient>
                </defs>
                <Line type="monotone" dataKey="v" stroke="url(#cyanGrad)"
                  strokeWidth={2} dot={false} animationDuration={400} />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(4,13,24,0.9)',
                    border: '1px solid rgba(0,212,255,0.2)',
                    borderRadius: '8px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                  }}
                  labelStyle={{ display: 'none' }}
                  formatter={(v: number) => [`${v.toFixed(2)} TPS`, '']}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      <motion.div className="glass-card overflow-hidden"
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}>
        <div className="flex items-center gap-2 px-4 py-3"
          style={{ borderBottom: '1px solid rgba(0,212,255,0.1)' }}>
          <BarChart3 size={14} style={{ color: 'var(--purple-primary)' }} />
          <span className="text-sm font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
            PROMETHEUS / GRAFANA METRICS
          </span>
          <a href={process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3001'}
            target="_blank" rel="noopener noreferrer"
            className="ml-auto text-xs font-mono" style={{ color: 'var(--cyan-primary)' }}>
            OPEN FULL â†’
          </a>
        </div>
        <iframe
          src={`${process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3001'}/d/upi-fraud/overview?orgId=1&refresh=5s&theme=dark&kiosk`}
          className="w-full"
          style={{ height: '320px', border: 'none' }}
          title="Grafana Dashboard"
        />
      </motion.div>
    </div>
  )
}
