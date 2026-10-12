import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import {
  getMe,
  googleLogin as apiGoogleLogin,
  login as apiLogin,
  register as apiRegister,
} from '../api/auth'
import { ApiError } from '../api/client'
import type { UserPublic } from '../api/types'
import { clearTokens, getAccessToken, setTokens } from './tokenStore'

// Esperas entre reintentos al restaurar la sesión (cubren el arranque en frío de Render).
const RESTORE_RETRY_DELAYS_MS = [2000, 5000, 10000, 20000]

type Status = 'loading' | 'authenticated' | 'anonymous'

interface AuthContextValue {
  user: UserPublic | null
  status: Status
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName?: string) => Promise<void>
  loginWithGoogle: (credential: string) => Promise<void>
  logout: () => void
  setUser: (user: UserPublic) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null)
  const [status, setStatus] = useState<Status>('loading')

  // Al cargar la app, si hay token guardado, validamos la sesión con /users/me.
  // Esto hace que la sesión sobreviva a recargas.
  // Solo un 401 invalida la sesión; ante errores de red o 5xx (p. ej. el backend
  // de Render despertando) reintentamos sin borrar los tokens.
  useEffect(() => {
    if (!getAccessToken()) {
      setStatus('anonymous')
      return
    }
    let cancelled = false
    async function restoreSession() {
      for (let attempt = 0; ; attempt++) {
        try {
          const me = await getMe()
          if (cancelled) return
          setUser(me)
          setStatus('authenticated')
          return
        } catch (err) {
          if (cancelled) return
          const unauthorized = err instanceof ApiError && err.status === 401
          if (unauthorized || attempt >= RESTORE_RETRY_DELAYS_MS.length) {
            if (unauthorized) clearTokens()
            setUser(null)
            setStatus('anonymous')
            return
          }
          await new Promise((r) => setTimeout(r, RESTORE_RETRY_DELAYS_MS[attempt]))
        }
      }
    }
    void restoreSession()
    return () => {
      cancelled = true
    }
  }, [])

  async function login(email: string, password: string) {
    setTokens(await apiLogin(email, password))
    setUser(await getMe())
    setStatus('authenticated')
  }

  async function register(email: string, password: string, displayName?: string) {
    setTokens(await apiRegister(email, password, displayName))
    setUser(await getMe())
    setStatus('authenticated')
  }

  async function loginWithGoogle(credential: string) {
    setTokens(await apiGoogleLogin(credential))
    setUser(await getMe())
    setStatus('authenticated')
  }

  function logout() {
    clearTokens()
    setUser(null)
    setStatus('anonymous')
  }

  return (
    <AuthContext.Provider
      value={{ user, status, login, register, loginWithGoogle, logout, setUser }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return ctx
}
