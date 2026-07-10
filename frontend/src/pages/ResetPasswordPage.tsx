import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { resetPassword } from '../api/auth'
import { ApiError } from '../api/client'
import AuthShell from '../components/AuthShell'
import { inputClass, labelClass, primaryButtonClass } from '../components/ui'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.')
      return
    }
    setSubmitting(true)
    try {
      await resetPassword(token, password)
      setDone(true)
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError('El enlace es inválido o ha caducado. Solicita uno nuevo.')
      } else {
        setError('No se pudo restablecer la contraseña. Inténtalo de nuevo.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      subtitle="Nueva contraseña"
      footer={
        <Link to="/login" className="font-medium text-brand-600 hover:underline">
          Volver al inicio de sesión
        </Link>
      }
    >
      {done ? (
        <p className="text-sm text-neutral-600 dark:text-neutral-300" role="status">
          ✅ Contraseña actualizada. Ya puedes{' '}
          <Link to="/login" className="font-medium text-brand-600 hover:underline">
            iniciar sesión
          </Link>{' '}
          con tu nueva contraseña.
        </p>
      ) : !token ? (
        <p className="text-sm text-red-600" role="alert">
          Falta el token del enlace. Abre el enlace completo que recibiste por email, o{' '}
          <Link to="/forgot-password" className="font-medium text-brand-600 hover:underline">
            solicita uno nuevo
          </Link>
          .
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="password" className={labelClass}>
              Nueva contraseña
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
            />
            <p className="mt-1 text-xs text-neutral-500">Mínimo 8 caracteres.</p>
          </div>
          {error && (
            <p className="text-sm text-red-600" role="alert">
              {error}
            </p>
          )}
          <button type="submit" disabled={submitting} className={primaryButtonClass}>
            {submitting ? 'Guardando…' : 'Guardar contraseña'}
          </button>
        </form>
      )}
    </AuthShell>
  )
}
