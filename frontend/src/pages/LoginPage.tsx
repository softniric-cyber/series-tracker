import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import AuthShell from '../components/AuthShell'
import GoogleAuthButton from '../components/GoogleAuthButton'
import { inputClass, labelClass, primaryButtonClass } from '../components/ui'
import { useAuth } from '../auth/AuthContext'

interface LocationState {
  from?: { pathname: string }
}

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const from = (location.state as LocationState | null)?.from?.pathname ?? '/'

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError('Email o contraseña incorrectos.')
      } else {
        setError('No se pudo iniciar sesión. Inténtalo de nuevo.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      subtitle="Entra en tu cuenta"
      footer={
        <>
          ¿No tienes cuenta?{' '}
          <Link to="/register" className="font-medium text-brand-600 hover:underline">
            Regístrate
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div>
          <label htmlFor="email" className={labelClass}>
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor="password" className={labelClass}>
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
          />
        </div>
        {error && (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
        <button type="submit" disabled={submitting} className={primaryButtonClass}>
          {submitting ? 'Entrando…' : 'Entrar'}
        </button>
        <p className="text-center text-sm">
          <Link to="/forgot-password" className="text-neutral-500 hover:text-brand-600 hover:underline">
            ¿Olvidaste tu contraseña?
          </Link>
        </p>
      </form>
      <div className="mt-5">
        <GoogleAuthButton redirectTo={from} />
      </div>
    </AuthShell>
  )
}
