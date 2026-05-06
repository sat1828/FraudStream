'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'

interface User {
  id: string
  email: string
  full_name: string | null
  is_superuser: boolean
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  login: (email: string, password: string) => Promise<boolean>
  logout: () => void
  clearError: () => void
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const COOKIE_NAME = 'upi-auth'

const setAuthCookie = (token: string | null, user: User | null) => {
  if (typeof document === 'undefined') return
  if (token && user) {
    const value = JSON.stringify({ state: { token, user, isAuthenticated: true } })
    document.cookie = `${COOKIE_NAME}=${encodeURIComponent(value)}; path=/; max-age=86400; SameSite=Lax`
  } else {
    document.cookie = `${COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax`
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await axios.post(`${API_URL}/api/v1/auth/login`, {
            email,
            password,
          })
          const { access_token, user } = response.data
          set({
            token: access_token,
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
          setAuthCookie(access_token, user)
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
          return true
        } catch (err: any) {
          set({
            isLoading: false,
            error: err.response?.data?.detail || 'Login failed',
            isAuthenticated: false,
          })
          return false
        }
      },

      logout: () => {
        delete axios.defaults.headers.common['Authorization']
        setAuthCookie(null, null)
        set({ token: null, user: null, isAuthenticated: false, error: null })
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'upi-auth',
      partialize: (state) => ({ token: state.token, user: state.user, isAuthenticated: state.isAuthenticated }),
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          axios.defaults.headers.common['Authorization'] = `Bearer ${state.token}`
          setAuthCookie(state.token, state.user)
        } else {
          setAuthCookie(null, null)
        }
      },
    }
  )
)
