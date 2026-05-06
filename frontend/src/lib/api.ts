import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 10000,
})

// Attach token from localStorage on each request
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    try {
      const auth = JSON.parse(localStorage.getItem('upi-auth') || '{}')
      const token = auth?.state?.token
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    } catch {}
  }
  return config
})

// Types
export interface Transaction {
  id: string
  transaction_id: string
  sender_vpa: string
  receiver_vpa: string
  amount: number
  city: string
  risk_score: number | null
  decision: 'ALLOW' | 'BLOCK' | 'REVIEW' | null
  inference_latency_ms: number | null
  initiated_at: string
}

export interface SystemMetrics {
  total_transactions: number
  transactions_last_hour: number
  fraud_rate_percent: number
  avg_latency_ms: number
  p95_latency_ms: number
  current_model_version: string
  drift_score: number
  last_retrain: string | null
  tps: number
}

export interface ModelVersion {
  id: number
  mlflow_run_id: string
  mlflow_version: string | null
  stage: string
  train_auc: number | null
  val_auc: number | null
  precision: number | null
  recall: number | null
  f1_score: number | null
  fpr: number | null
  drift_score: number | null
  triggered_by_drift: boolean
  training_samples: number | null
  is_active: boolean
  created_at: string
}

export interface DriftReport {
  id: number
  report_id: string
  window_start: string
  window_end: string
  transaction_count: number
  dataset_drift_score: number
  n_drifted_features: number
  drifted_features: string[]
  drift_detected: boolean
  retrain_triggered: boolean
  created_at: string
}

export const fetchMetrics = () => api.get<SystemMetrics>('/metrics').then(r => r.data)
export const fetchTransactions = (page = 1, decision?: string) =>
  api.get('/transactions', { params: { page, page_size: 50, decision } }).then(r => r.data)
export const fetchModels = () => api.get<ModelVersion[]>('/models').then(r => r.data)
export const fetchDriftReports = () => api.get<DriftReport[]>('/drift-reports').then(r => r.data)
export const promoteModel = (id: number) => api.post(`/models/${id}/promote`).then(r => r.data)
export const rollbackModel = () => api.post('/models/rollback').then(r => r.data)
