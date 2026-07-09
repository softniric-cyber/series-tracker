import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { getMe, login as apiLogin, register as apiRegister } from '../api/auth'
import type { UserPublic } from '../api/types'
import { clearTokens, getAccessToken, setTokens } from './tokenStore'

type Status = 'loading' | 'authenticated' | 'anonymous'

interface AuthContextValue {
  user: UserPublic | null
  status: Status
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName?: string) => Promise<void>
  logout: () => void
  setUser: (user: UserPublic) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null)
  const [status, setStatus] = useState<Status>('loading')

  // Al cargar la app, si hay token guardado, validamos la sesión con /users/me.
  // Esto hace que la sesión sobreviva a recargas.
  useEffect(() => {
    if (!getAccessToken()) {
      setStatus('anonymous')
      return
    }
    getMe()
      .then((me) => {
        setUser(me)
        setStatus('authenticated')
      })
      .catch(() => {
        clearTokens()
        setUser(null)
        setStatus('anonymous')
      })
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

  function logout() {
    clearTokens()
    setUser(null)
    setStatus('anonymous')
  }

  return (
    <AuthContext.Provider value={{ user, status, login, register, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return ctx
}
