'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/auth-store'

export default function HomePage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()

  useEffect(() => {
    router.replace(isAuthenticated ? '/dashboard' : '/auth')
  }, [isAuthenticated, router])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="inline-block w-8 h-8 border-2 rounded-full animate-spin"
          style={{ borderColor: 'rgba(0,212,255,0.2)', borderTopColor: 'var(--cyan-primary)' }} />
        <p className="mt-3 text-xs font-mono" style={{ color: 'var(--text-muted)' }}>INITIALIZING...</p>
      </div>
    </div>
  )
}
