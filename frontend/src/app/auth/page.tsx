'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Shield, Eye, EyeOff, Zap, Lock, Terminal } from 'lucide-react'
import { useAuthStore } from '@/lib/auth-store'

export default function LoginPage() {
  const [email, setEmail] = useState('admin@upi.ai')
  const [password, setPassword] = useState('password')
  const [showPassword, setShowPassword] = useState(false)
  const [mounted, setMounted] = useState(false)
  const router = useRouter()
  const { login, isLoading, error, isAuthenticated, clearError } = useAuthStore()

  useEffect(() => {
    setMounted(true)
    if (isAuthenticated) router.replace('/dashboard')
  }, [isAuthenticated, router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const success = await login(email, password)
    if (success) router.replace('/dashboard')
  }

  if (!mounted) return null

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Animated background orbs */}
      <div className="fixed inset-0 pointer-events-none">
        <motion.div
          className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(0,212,255,0.08) 0%, transparent 70%)' }}
          animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(168,85,247,0.1) 0%, transparent 70%)' }}
          animate={{ scale: [1, 1.3, 1], opacity: [0.4, 0.7, 0.4] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
        />
        {/* Grid overlay */}
        <div className="absolute inset-0" style={{
          backgroundImage: 'linear-gradient(rgba(0,212,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,0.04) 1px, transparent 1px)',
          backgroundSize: '40px 40px'
        }} />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-md mx-4"
      >
        {/* Main login card */}
        <div className="glass-card p-8 glow-cyan">
          {/* Header */}
          <div className="text-center mb-8">
            <motion.div
              className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4"
              style={{ background: 'linear-gradient(135deg, rgba(0,212,255,0.2), rgba(168,85,247,0.2))', border: '1px solid rgba(0,212,255,0.3)' }}
              animate={{ boxShadow: ['0 0 20px rgba(0,212,255,0.2)', '0 0 40px rgba(0,212,255,0.4)', '0 0 20px rgba(0,212,255,0.2)'] }}
              transition={{ duration: 3, repeat: Infinity }}
            >
              <Shield size={28} style={{ color: 'var(--cyan-primary)' }} />
            </motion.div>

            <h1 className="text-2xl font-bold mb-1" style={{ fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>
              UPI FRAUD SHIELD
            </h1>
            <p className="text-sm" style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
              ML-POWERED DETECTION SYSTEM v1.0
            </p>

            {/* Live indicator */}
            <div className="flex items-center justify-center mt-3 gap-2">
              <div className="live-dot" />
              <span className="text-xs font-mono" style={{ color: 'var(--green-primary)' }}>SYSTEM ONLINE</span>
            </div>
          </div>

          {/* Terminal-style label */}
          <div className="mb-4 px-3 py-2 rounded" style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(0,212,255,0.1)' }}>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
              <span style={{ color: 'var(--cyan-primary)' }}>$</span> authenticate --role=analyst --system=fraud-detection
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono mb-1.5" style={{ color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                OPERATOR EMAIL
              </label>
              <input
                type="email"
                value={email}
                onChange={e => { setEmail(e.target.value); clearError() }}
                className="glass-input"
                placeholder="admin@upi.ai"
                required
                autoComplete="email"
              />
            </div>

            <div>
              <label className="block text-xs font-mono mb-1.5" style={{ color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                ACCESS KEY
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => { setPassword(e.target.value); clearError() }}
                  className="glass-input pr-10"
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="px-3 py-2 rounded text-sm font-mono"
                  style={{ background: 'rgba(255,45,85,0.1)', border: '1px solid rgba(255,45,85,0.3)', color: 'var(--red-primary)' }}
                >
                  ⚠ {error}
                </motion.div>
              )}
            </AnimatePresence>

            <motion.button
              type="submit"
              disabled={isLoading}
              className="glass-button glass-button-primary w-full py-3 relative overflow-hidden"
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <motion.div
                    className="w-4 h-4 border-2 rounded-full"
                    style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'white' }}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                  />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>AUTHENTICATING...</span>
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2" style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', letterSpacing: '0.1em' }}>
                  <Zap size={14} />
                  AUTHORIZE ACCESS
                </span>
              )}
            </motion.button>
          </form>

          {/* Demo credentials hint */}
          <div className="mt-6 pt-4" style={{ borderTop: '1px solid rgba(0,212,255,0.1)' }}>
            <p className="text-center text-xs font-mono mb-2" style={{ color: 'var(--text-muted)' }}>DEMO CREDENTIALS</p>
            <div className="grid grid-cols-2 gap-2">
              <div className="px-3 py-2 rounded text-xs font-mono" style={{ background: 'rgba(0,0,0,0.3)', color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--cyan-primary)' }}>email: </span>admin@upi.ai
              </div>
              <div className="px-3 py-2 rounded text-xs font-mono" style={{ background: 'rgba(0,0,0,0.3)', color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--cyan-primary)' }}>pass: </span>password
              </div>
            </div>
          </div>
        </div>

        {/* Tech stack badges */}
        <div className="flex justify-center gap-2 mt-4 flex-wrap">
          {['XGBoost', 'SHAP', 'MLflow', 'Feast', 'FastAPI'].map((tech, i) => (
            <motion.span
              key={tech}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + i * 0.08 }}
              className="px-2 py-0.5 rounded text-xs font-mono"
              style={{ background: 'rgba(0,212,255,0.06)', border: '1px solid rgba(0,212,255,0.12)', color: 'var(--text-muted)' }}
            >
              {tech}
            </motion.span>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
