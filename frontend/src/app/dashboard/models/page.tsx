'use client'

import { motion } from 'framer-motion'
import { GitBranch, CheckCircle2, Archive, Clock, TrendingUp, RotateCcw, ChevronUp } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchModels, promoteModel, rollbackModel } from '@/lib/api'
import { format } from 'date-fns'
import { useState } from 'react'

export default function ModelsPage() {
  const queryClient = useQueryClient()
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const { data: models = [], isLoading } = useQuery({
    queryKey: ['models'],
    queryFn: fetchModels,
    refetchInterval: 10000,
  })

  const promoteMutation = useMutation({
    mutationFn: promoteModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] })
      setActionMsg('✓ Model promoted to Production')
      setTimeout(() => setActionMsg(null), 3000)
    },
  })

  const rollbackMutation = useMutation({
    mutationFn: rollbackModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] })
      setActionMsg('✓ Rolled back to previous version')
      setTimeout(() => setActionMsg(null), 3000)
    },
  })

  return (
    <div className="p-6 space-y-5 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold" style={{ fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>
            MODEL REGISTRY
          </h1>
          <p className="text-xs font-mono mt-0.5" style={{ color: 'var(--text-muted)' }}>
            MLflow model versions — promote, rollback, compare
          </p>
        </div>
        <motion.button
          className="glass-button flex items-center gap-1.5 text-xs"
          style={{ borderColor: 'rgba(255,45,85,0.3)', color: 'var(--red-primary)' }}
          onClick={() => rollbackMutation.mutate()}
          disabled={rollbackMutation.isPending}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <RotateCcw size={12} />
          ROLLBACK
        </motion.button>
      </div>

      {actionMsg && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="px-4 py-2 rounded-lg text-sm font-mono"
          style={{ background: 'rgba(0,255,157,0.08)', border: '1px solid rgba(0,255,157,0.2)', color: 'var(--green-primary)' }}
        >
          {actionMsg}
        </motion.div>
      )}

      {/* Models grid */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="text-center py-10 text-sm font-mono" style={{ color: 'var(--text-muted)' }}>Loading models...</div>
        ) : models.length === 0 ? (
          <div className="glass-card p-8 text-center">
            <GitBranch size={32} className="mx-auto mb-3" style={{ color: 'var(--text-muted)' }} />
            <p className="text-sm font-mono" style={{ color: 'var(--text-muted)' }}>
              No models registered yet. Training will begin automatically.
            </p>
          </div>
        ) : (
          models.map((model: any, i: number) => (
            <motion.div
              key={model.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="glass-card p-5"
              style={{
                borderColor: model.is_active ? 'rgba(0,255,157,0.25)' : 'rgba(0,212,255,0.1)',
              }}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{
                      background: model.is_active ? 'rgba(0,255,157,0.1)' : 'rgba(0,212,255,0.06)',
                      border: `1px solid ${model.is_active ? 'rgba(0,255,157,0.3)' : 'rgba(0,212,255,0.15)'}`,
                    }}
                  >
                    {model.is_active ? (
                      <CheckCircle2 size={16} style={{ color: 'var(--green-primary)' }} />
                    ) : model.stage === 'Archived' ? (
                      <Archive size={16} style={{ color: 'var(--text-muted)' }} />
                    ) : (
                      <Clock size={16} style={{ color: 'var(--cyan-primary)' }} />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
                        {model.model_name} v{model.mlflow_version ?? '?'}
                      </span>
                      {model.is_active && (
                        <span className="badge-allow text-xs">PRODUCTION</span>
                      )}
                      {model.triggered_by_drift && (
                        <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: 'rgba(255,184,0,0.1)', border: '1px solid rgba(255,184,0,0.2)', color: 'var(--amber-primary)' }}>
                          DRIFT-TRIGGERED
                        </span>
                      )}
                    </div>
                    <div className="text-xs font-mono mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      Run: {model.mlflow_run_id.slice(0, 12)}... • {format(new Date(model.created_at), 'dd MMM yyyy HH:mm')}
                    </div>
                  </div>
                </div>
                {!model.is_active && model.stage !== 'Archived' && (
                  <motion.button
                    className="glass-button text-xs flex items-center gap-1"
                    onClick={() => promoteMutation.mutate(model.id)}
                    disabled={promoteMutation.isPending}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <ChevronUp size={12} />
                    PROMOTE
                  </motion.button>
                )}
              </div>

              {/* Metrics row */}
              {(model.val_auc || model.precision || model.recall) && (
                <div className="grid grid-cols-5 gap-3 mt-4 pt-4" style={{ borderTop: '1px solid rgba(0,212,255,0.08)' }}>
                  {[
                    { label: 'AUC', value: model.val_auc, color: 'var(--cyan-primary)' },
                    { label: 'PRECISION', value: model.precision, color: 'var(--purple-primary)' },
                    { label: 'RECALL', value: model.recall, color: 'var(--green-primary)' },
                    { label: 'F1', value: model.f1_score, color: 'var(--amber-primary)' },
                    { label: 'FPR', value: model.fpr, color: 'var(--red-primary)', scale: 10000 },
                  ].map(({ label, value, color, scale }) => (
                    <div key={label} className="text-center">
                      <div className="text-sm font-mono font-bold" style={{ color }}>
                        {value != null ? scale ? `${(value * (scale)).toFixed(2)}‱` : value.toFixed(4) : '—'}
                      </div>
                      <div className="text-xs font-mono mt-0.5" style={{ color: 'var(--text-muted)' }}>{label}</div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          ))
        )}
      </div>

      {/* MLflow link */}
      <div className="text-center">
        <a
          href="http://localhost:5000"
          target="_blank"
          rel="noopener noreferrer"
          className="glass-button inline-flex items-center gap-2 text-xs"
        >
          <TrendingUp size={12} />
          OPEN MLFLOW UI
        </a>
      </div>
    </div>
  )
}
