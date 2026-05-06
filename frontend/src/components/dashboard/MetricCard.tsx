'use client'

import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface MetricCardProps {
  label: string
  value: number | string
  unit?: string
  icon: LucideIcon
  color: 'cyan' | 'purple' | 'green' | 'red' | 'amber'
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  description?: string
  animate?: boolean
  precision?: number
}

const COLOR_MAP = {
  cyan:   { primary: 'var(--cyan-primary)',   glow: 'rgba(0,212,255,0.15)',   border: 'rgba(0,212,255,0.2)' },
  purple: { primary: 'var(--purple-primary)', glow: 'rgba(168,85,247,0.15)', border: 'rgba(168,85,247,0.2)' },
  green:  { primary: 'var(--green-primary)',  glow: 'rgba(0,255,157,0.12)',   border: 'rgba(0,255,157,0.2)' },
  red:    { primary: 'var(--red-primary)',    glow: 'rgba(255,45,85,0.12)',   border: 'rgba(255,45,85,0.2)' },
  amber:  { primary: 'var(--amber-primary)',  glow: 'rgba(255,184,0,0.12)',   border: 'rgba(255,184,0,0.2)' },
}

function useAnimatedCounter(target: number, duration = 1000, precision = 0) {
  const [current, setCurrent] = useState(0)
  const raf = useRef<number | null>(null)
  const startTime = useRef<number | null>(null)
  const startValue = useRef(0)

  useEffect(() => {
    startValue.current = current
    startTime.current = null

    const step = (timestamp: number) => {
      if (!startTime.current) startTime.current = timestamp
      const progress = Math.min((timestamp - startTime.current) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3) // ease out cubic
      const value = startValue.current + (target - startValue.current) * eased
      setCurrent(parseFloat(value.toFixed(precision)))
      if (progress < 1) raf.current = requestAnimationFrame(step)
    }

    raf.current = requestAnimationFrame(step)
    return () => { if (raf.current) cancelAnimationFrame(raf.current) }
  }, [target])

  return current
}

export default function MetricCard({
  label, value, unit, icon: Icon, color, trend, trendValue, description, animate = true, precision = 0
}: MetricCardProps) {
  const colors = COLOR_MAP[color]
  const numericValue = typeof value === 'number' ? value : parseFloat(value as string) || 0
  const animatedValue = useAnimatedCounter(numericValue, 800, precision)
  const displayValue = animate && typeof value === 'number'
    ? precision > 0 ? animatedValue.toFixed(precision) : Math.round(animatedValue).toLocaleString()
    : typeof value === 'number'
      ? precision > 0 ? value.toFixed(precision) : value.toLocaleString()
      : value

  return (
    <motion.div
      className="glass-card p-5 relative overflow-hidden"
      style={{ borderColor: colors.border }}
      whileHover={{ scale: 1.01, borderColor: colors.primary }}
      transition={{ duration: 0.2 }}
    >
      {/* Background glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: `radial-gradient(ellipse at 80% 20%, ${colors.glow}, transparent 60%)` }}
      />

      {/* Header row */}
      <div className="flex items-start justify-between mb-3 relative">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: `${colors.glow}`, border: `1px solid ${colors.border}` }}
        >
          <Icon size={15} style={{ color: colors.primary }} />
        </div>

        {trend && (
          <div className="flex items-center gap-1 text-xs font-mono">
            {trend === 'up' && <TrendingUp size={12} style={{ color: color === 'red' ? 'var(--red-primary)' : 'var(--green-primary)' }} />}
            {trend === 'down' && <TrendingDown size={12} style={{ color: color === 'green' ? 'var(--red-primary)' : 'var(--green-primary)' }} />}
            {trend === 'neutral' && <Minus size={12} style={{ color: 'var(--text-muted)' }} />}
            {trendValue && (
              <span style={{ color: trend === 'neutral' ? 'var(--text-muted)' : trend === 'up' ? (color === 'red' ? 'var(--red-primary)' : 'var(--green-primary)') : 'var(--red-primary)' }}>
                {trendValue}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Value */}
      <div className="relative">
        <div className="flex items-end gap-1.5">
          <motion.span
            key={displayValue}
            className="kpi-value"
            style={{ color: colors.primary }}
            initial={{ opacity: 0.6 }}
            animate={{ opacity: 1 }}
          >
            {displayValue}
          </motion.span>
          {unit && (
            <span className="text-sm font-mono mb-1" style={{ color: 'var(--text-muted)' }}>
              {unit}
            </span>
          )}
        </div>

        <div className="text-xs font-mono mt-1.5 uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
          {label}
        </div>

        {description && (
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            {description}
          </div>
        )}
      </div>

      {/* Bottom accent line */}
      <motion.div
        className="absolute bottom-0 left-0 h-0.5 rounded-full"
        style={{ background: `linear-gradient(90deg, ${colors.primary}, transparent)` }}
        initial={{ width: '0%' }}
        animate={{ width: '60%' }}
        transition={{ duration: 1.2, delay: 0.3, ease: 'easeOut' }}
      />
    </motion.div>
  )
}
