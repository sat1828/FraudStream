'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Shield, LayoutDashboard, Activity, GitBranch,
  BarChart3, Network, LogOut, ChevronLeft, Terminal, Zap
} from 'lucide-react'
import { useAuthStore } from '@/lib/auth-store'

const NAV_ITEMS = [
  { href: '/dashboard', label: 'OVERVIEW', icon: LayoutDashboard, description: 'KPIs & live feed' },
  { href: '/dashboard/transactions', label: 'TRANSACTIONS', icon: Activity, description: 'Live scoring log' },
  { href: '/dashboard/network', label: 'THREAT MAP', icon: Network, description: '3D transaction graph' },
  { href: '/dashboard/models', label: 'MODEL REGISTRY', icon: GitBranch, description: 'MLflow versions' },
  { href: '/dashboard/monitoring', label: 'DRIFT MONITOR', icon: BarChart3, description: 'Evidently reports' },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const [collapsed, setCollapsed] = useState(false)

  const handleLogout = () => {
    logout()
    router.replace('/auth')
  }

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 220 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="flex flex-col h-full relative"
      style={{
        background: 'rgba(4, 13, 24, 0.95)',
        backdropFilter: 'blur(20px)',
        borderRight: '1px solid rgba(0,212,255,0.1)',
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <div className="p-4 flex items-center gap-3" style={{ borderBottom: '1px solid rgba(0,212,255,0.08)' }}>
        <motion.div
          className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, rgba(0,212,255,0.3), rgba(168,85,247,0.3))', border: '1px solid rgba(0,212,255,0.3)' }}
          animate={{ boxShadow: ['0 0 10px rgba(0,212,255,0.2)', '0 0 20px rgba(0,212,255,0.4)', '0 0 10px rgba(0,212,255,0.2)'] }}
          transition={{ duration: 3, repeat: Infinity }}
        >
          <Shield size={16} style={{ color: 'var(--cyan-primary)' }} />
        </motion.div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
            >
              <div className="text-xs font-bold leading-none" style={{ fontFamily: 'var(--font-mono)', color: 'var(--cyan-primary)', letterSpacing: '0.05em' }}>
                UPI SHIELD
              </div>
              <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                FRAUD OPS
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Nav links */}
      <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto overflow-x-hidden">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href))
          const Icon = item.icon

          return (
            <Link key={item.href} href={item.href}>
              <motion.div
                className={`sidebar-link ${isActive ? 'active' : ''}`}
                title={collapsed ? item.label : undefined}
                whileHover={{ x: collapsed ? 0 : 2 }}
                transition={{ duration: 0.15 }}
              >
                <Icon size={16} style={{ flexShrink: 0, color: isActive ? 'var(--cyan-primary)' : 'currentColor' }} />
                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-xs font-mono truncate"
                      style={{ letterSpacing: '0.08em' }}
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
                {isActive && (
                  <motion.div
                    layoutId="active-indicator"
                    className="absolute right-0 w-0.5 h-5 rounded-full"
                    style={{ background: 'var(--cyan-primary)', boxShadow: '0 0 8px var(--cyan-primary)' }}
                  />
                )}
              </motion.div>
            </Link>
          )
        })}
      </nav>

      {/* Bottom section */}
      <div className="p-2 space-y-1" style={{ borderTop: '1px solid rgba(0,212,255,0.08)' }}>
        {/* User info */}
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="px-3 py-2 rounded-lg"
              style={{ background: 'rgba(0,212,255,0.04)' }}
            >
              <div className="text-xs font-mono truncate" style={{ color: 'var(--text-secondary)' }}>
                {user?.email}
              </div>
              <div className="text-xs font-mono mt-0.5" style={{ color: 'var(--text-muted)' }}>
                {user?.is_superuser ? 'SUPERUSER' : 'ANALYST'}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(v => !v)}
          className="sidebar-link w-full"
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          <motion.div animate={{ rotate: collapsed ? 180 : 0 }}>
            <ChevronLeft size={16} />
          </motion.div>
          <AnimatePresence>
            {!collapsed && (
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-xs font-mono">
                COLLAPSE
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {/* Logout */}
        <button onClick={handleLogout} className="sidebar-link w-full" title={collapsed ? 'Logout' : undefined}>
          <LogOut size={16} style={{ color: 'var(--red-primary)' }} />
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="text-xs font-mono"
                style={{ color: 'var(--red-primary)' }}
              >
                DISCONNECT
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  )
}
