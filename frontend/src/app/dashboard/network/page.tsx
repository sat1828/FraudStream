'use client'

import dynamic from 'next/dynamic'
import { motion } from 'framer-motion'
import { Info, RefreshCw } from 'lucide-react'
import { useState } from 'react'

// SSR=false — Three.js requires browser APIs
const NetworkGraph3D = dynamic(() => import('@/components/3d/NetworkGraph3D'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <motion.div
          className="w-10 h-10 border-2 rounded-full mx-auto mb-3"
          style={{ borderColor: 'rgba(0,212,255,0.2)', borderTopColor: 'var(--cyan-primary)' }}
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        />
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          Initialising 3D threat graph…
        </p>
      </div>
    </div>
  ),
})

const LEGEND = [
  { color: '#00d4ff', label: 'Normal VPA',      desc: 'Legitimate user account' },
  { color: '#ff2d55', label: 'Fraud / Mule',    desc: 'Flagged mule account — pulsing' },
  { color: '#a855f7', label: 'Merchant',         desc: 'Verified merchant VPA' },
  { color: '#ffb800', label: 'Under Review',     desc: 'Pending manual check' },
]

const EDGE_LEGEND = [
  { color: '#00d4ff', opacity: 0.6, label: 'Legitimate transaction' },
  { color: '#ff2d55', opacity: 0.9, label: 'Fraudulent flow' },
]

export default function NetworkPage() {
  const [key, setKey] = useState(0)  // remount to regenerate graph

  return (
    <div className="p-6 space-y-4 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold"
            style={{ fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>
            THREAT NETWORK MAP
          </h1>
          <p className="text-xs font-mono mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Force-directed 3D graph — fraud clusters self-organise under physics simulation
          </p>
        </div>
        <motion.button
          className="glass-button flex items-center gap-1.5 text-xs"
          onClick={() => setKey(k => k + 1)}
          whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
        >
          <RefreshCw size={12} /> REGENERATE
        </motion.button>
      </div>

      {/* Controls hint */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg"
        style={{ background: 'rgba(0,212,255,0.04)', border: '1px solid rgba(0,212,255,0.1)' }}>
        <Info size={13} style={{ color: 'var(--cyan-primary)', flexShrink: 0 }} />
        <span className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
          Drag to rotate · Scroll to zoom · Hover nodes for details · Fraud nodes pulse red · Force simulation active
        </span>
      </div>

      {/* Legend row */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <span className="text-xs font-mono uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
          Nodes:
        </span>
        {LEGEND.map(({ color, label, desc }) => (
          <div key={label} className="flex items-center gap-2" title={desc}>
            <motion.div
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ background: color, boxShadow: `0 0 6px ${color}` }}
              animate={label.includes('Fraud') ? { scale: [1, 1.35, 1], opacity: [0.7, 1, 0.7] } : {}}
              transition={label.includes('Fraud') ? { duration: 1.4, repeat: Infinity } : {}}
            />
            <span className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>{label}</span>
          </div>
        ))}
        <span className="text-xs font-mono uppercase tracking-wider ml-4" style={{ color: 'var(--text-muted)' }}>
          Edges:
        </span>
        {EDGE_LEGEND.map(({ color, label }) => (
          <div key={label} className="flex items-center gap-2">
            <div className="w-5 h-0.5 rounded" style={{ background: color }} />
            <span className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>{label}</span>
          </div>
        ))}
      </div>

      {/* 3D Canvas */}
      <motion.div
        className="glass-card overflow-hidden"
        style={{ height: '580px' }}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <NetworkGraph3D key={key} />
      </motion.div>

      {/* Stats footer */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'NORMAL VPAs',    value: '30', color: '#00d4ff' },
          { label: 'FRAUD NODES',    value: '8',  color: '#ff2d55' },
          { label: 'MERCHANTS',      value: '8',  color: '#a855f7' },
          { label: 'FRAUD EDGES',    value: '37', color: '#ffb800' },
        ].map(({ label, value, color }) => (
          <div key={label} className="glass-card p-3 text-center">
            <div className="text-lg font-mono font-bold" style={{ color }}>{value}</div>
            <div className="text-xs font-mono mt-0.5" style={{ color: 'var(--text-muted)' }}>{label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
