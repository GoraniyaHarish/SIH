import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from 'react'
import type { ReactNode } from 'react'
import { api, setUnauthorizedHandler, type User } from './api'

interface AuthState {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  can: (role: 'admin' | 'manager' | 'assessor' | 'staff') => boolean
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    try {
      const me = await api.get<User>('/auth/me')
      setUser(me)
    } catch {
      setUser(null)
    }
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null))
    // Session bootstrap: a valid refresh cookie restores the session on reload.
    ;(async () => {
      try {
        const me = await api.get<User>('/auth/me')
        setUser(me)
      } catch {
        setUser(null)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<{ user: User }>('/auth/login', { email, password })
    setUser(res.user)
    return res.user
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } finally {
      setUser(null)
    }
  }, [])

  const can = useCallback(
    (role: 'admin' | 'manager' | 'assessor' | 'staff') => {
      if (!user) return false
      if (role === 'admin') return user.role === 'admin'
      if (role === 'staff') return ['admin', 'manager', 'assessor'].includes(user.role)
      if (role === 'manager') return ['admin', 'manager'].includes(user.role)
      return ['admin', 'assessor'].includes(user.role)
    },
    [user],
  )

  const value = useMemo(
    () => ({ user, loading, login, logout, refreshUser, can }),
    [user, loading, login, logout, refreshUser, can],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
