'use client'

import { motion } from 'framer-motion'
import { BarChart3, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { fetchDriftReports } from '@/lib/api'
import { format } from 'date-fns'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts'

export default function MonitoringPage() {
  const { data: reports = [], isLoading, refetch, isFetching } = useQuery({
    queryKey: ['drift-reports'],
    queryFn: fetchDriftReports,
    refetchInterval: 15000,
  })

  const chartData = [...reports].reverse().map((r: any, i: number) => ({
    idx: i + 1,
    score: parseFloat((r.dataset_drift_score * 100).toFixed(2)),
    threshold: 10,
    drifted: r.drift_detected,
  }))

  return (
    <div className="p-6 space-y-5 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold" style={{ fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>
            DRIFT MONITOR
          </h1>
          <p className="text-xs font-mono mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Evidently AI feature & prediction drift detection
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="glass-button flex items-center gap-1.5 text-xs"
        >
          <motion.div animate={isFetching ? { rotate: 360 } : { rotate: 0 }} transition={{ duration: 0.8, repeat: isFetching ? Infinity : 0, ease: 'linear' }}>
            <RefreshCw size={12} />
          </motion.div>
          REFRESH
        </button>
      </div>

      {/* Drift score timeline */}
      {chartData.length > 0 && (
        <motion.div
          className="glass-card p-5"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 size={14} style={{ color: 'var(--purple-primary)' }} />
            <span className="text-sm font-mono font-bold" style={{ color: 'var(--text-primary)' }}>DRIFT SCORE TIMELINE</span>
            <span className="text-xs font-mono ml-auto" style={{ color: 'var(--text-muted)' }}>Threshold: 10%</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="driftGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#a855f7" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#a855f7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="idx" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }} unit="%" />
              <Tooltip
                contentStyle={{ background: 'rgba(4,13,24,0.95)', border: '1px solid rgba(168,85,247,0.3)', borderRadius: '8px', fontFamily: 'var(--font-mono)', fontSize: '11px' }}
                formatter={(v: number) => [`${v.toFixed(2)}%`, 'Drift Score']}
              />
              <ReferenceLine y={10} stroke="rgba(255,45,85,0.5)" strokeDasharray="4 4" label={{ value: 'THRESHOLD', fill: 'var(--red-primary)', fontSize: 10, fontFamily: 'var(--font-mono)' }} />
              <Area type="monotone" dataKey="score" stroke="#a855f7" fill="url(#driftGrad)" strokeWidth={2} dot={(props) => {
                const { cx, cy, payload } = props
                return payload.drifted ? (
                  <circle key={`dot-${cx}`} cx={cx} cy={cy} r={5} fill="var(--red-primary)" stroke="rgba(255,45,85,0.4)" strokeWidth={2} />
                ) : <circle key={`dot-${cx}`} cx={cx} cy={cy} r={3} fill="var(--purple-primary)" />
              }} />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>
      )}

      {/* Reports list */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="text-center py-10 text-sm font-mono" style={{ color: 'var(--text-muted)' }}>Loading reports...</div>
        ) : reports.length === 0 ? (
          <div className="glass-card p-8 text-center">
            <BarChart3 size={32} className="mx-auto mb-3" style={{ color: 'var(--text-muted)' }} />
            <p className="text-sm font-mono" style={{ color: 'var(--text-muted)' }}>
              Drift monitoring starts after 500 transactions are processed.
            </p>
          </div>
        ) : (
          reports.map((report: any, i: number) => (
            <motion.div
              key={report.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.04 }}
              className="glass-card p-4"
              style={{
                borderColor: report.drift_detected ? 'rgba(255,45,85,0.25)' : 'rgba(0,212,255,0.1)',
              }}
            >
              <div className="flex items-start gap-3">
                <div
                  className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{
                    background: report.drift_detected ? 'rgba(255,45,85,0.1)' : 'rgba(0,255,157,0.08)',
                  }}
                >
                  {report.drift_detected ? (
                    <AlertTriangle size={14} style={{ color: 'var(--red-primary)' }} />
                  ) : (
                    <CheckCircle size={14} style={{ color: 'var(--green-primary)' }} />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-mono font-bold" style={{ color: report.drift_detected ? 'var(--red-primary)' : 'var(--green-primary)' }}>
                      {report.drift_detected ? '⚡ DRIFT DETECTED' : '✓ NO DRIFT'}
                    </span>
                    <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                      {format(new Date(report.created_at), 'dd MMM HH:mm:ss')}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-3 mt-2">
                    <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                      Score: <span style={{ color: report.drift_detected ? 'var(--red-primary)' : 'var(--green-primary)', fontWeight: 700 }}>
                        {(report.dataset_drift_score * 100).toFixed(2)}%
                      </span>
                    </span>
                    <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                      Window: {report.transaction_count} txns
                    </span>
                    <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                      Drifted features: <span style={{ color: 'var(--amber-primary)' }}>{report.n_drifted_features}</span>
                    </span>
                    {report.retrain_triggered && (
                      <span className="text-xs font-mono px-2 py-0.5 rounded" style={{ background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.15)', color: 'var(--cyan-primary)' }}>
                        RETRAIN TRIGGERED
                      </span>
                    )}
                  </div>
                  {report.drifted_features?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {report.drifted_features.slice(0, 5).map((f: string) => (
                        <span key={f} className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: 'rgba(255,184,0,0.08)', color: 'var(--amber-primary)', border: '1px solid rgba(255,184,0,0.15)' }}>
                          {f}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  )
}
